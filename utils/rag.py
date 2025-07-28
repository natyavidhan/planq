import os
import time
import faiss
import numpy as np
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from bs4 import BeautifulSoup
import re
import json
from utils.database import Database


class RAG:
    def __init__(self, db: Database):
        _start = time.time()
        genai.configure(api_key=os.getenv("GEMINI_KEY"))
        self.gemini = genai.GenerativeModel("gemini-2.0-flash")
        self.model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")
        self.db = db

        self.INDEX_DIR = "faiss_indexes"
        os.makedirs(self.INDEX_DIR, exist_ok=True)

        self.exams = [
            "b3b5a8d8-f409-4e01-8fd4-043d3055db5e",  # JEE Main
            "f3e78517-c050-4fea-822b-e43c4d2d3523",  # WBJEE
            "4625ad6f-33db-4c22-96e0-6c23830482de",  # NEET
            "c8da26c7-cf1b-421f-829b-c95dbdd3cc6a",  # BITSAT
        ]

        self.indexes = {
            exam_id: self.load_exam_index(exam_id) for exam_id in self.exams
        }
        print(f"RAG initialized in {time.time() - _start:.2f} seconds")

    def clean_html(self, text):
        return BeautifulSoup(text, "html.parser").get_text()

    def clean_latex(self, text):
        return re.sub(r"\$[^\$]*\$", "", text)

    def preprocess_text(self, text):
        return self.clean_latex(self.clean_html(text)).strip()

    def load_exam_index(self, exam_id):
        faiss_file = f"{self.INDEX_DIR}/{exam_id}_index.faiss"
        ids_file = f"{self.INDEX_DIR}/{exam_id}_ids.npy"

        if not (os.path.exists(faiss_file) and os.path.exists(ids_file)):
            print(
                f"Index files for {exam_id} not found. Please generate embeddings first."
            )
            return None, None
        index = faiss.read_index(faiss_file)
        ids = np.load(ids_file, allow_pickle=True)

        return index, ids

    def retrieve_hybrid(
        self, query, exam_id, subject_id=None, chapter_id=None, top_k=5, alpha=0.6
    ):
        index, ids = self.indexes[exam_id]
        if index is None:
            return []

        query_emb = self.model.encode(query).astype("float32").reshape(1, -1)

        D, I = index.search(query_emb, top_k * 20)  # search more, filter later
        results = []

        for idx, dist in zip(I[0], D[0]):
            q_id = ids[idx]
            meta = self.db.pyqs["questions"].get(q_id, None)
            if not meta:
                continue

            if subject_id and meta["subject"] != subject_id:
                continue
            if chapter_id and meta["chapter"] != chapter_id:
                continue

            results.append((meta, 1 - dist))  # similarity = 1 - L2 distance

        if not results:
            return []

        tokenized_corpus = [r[0]["question"].split() for r in results]
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(query.split())

        sims = np.array([r[1] for r in results])
        bm25_norm = (bm25_scores - bm25_scores.min()) / (np.ptp(bm25_scores) + 1e-6)

        hybrid_scores = alpha * sims + (1 - alpha) * bm25_norm
        ranked = sorted(zip(results, hybrid_scores), key=lambda x: x[1], reverse=True)

        return [
            {
                "_id": r[0]["_id"],
                "raw_q": r[0]["question"],
                "question": self.preprocess_text(r[0]["question"]),
                "score": round(s, 4),
                "explanation": self.preprocess_text(r[0].get("explanation")),
            }
            for r, s in ranked[:top_k]
        ]

    def generate_embeddings(self):
        for exam_id in self.exams:
            cursor = [
                {"_id": i["_id"], "question": i["question"]}
                for i in self.db.pyqs["questions"].values()
                if i.get("exam") == exam_id
            ]
            all_embeddings, all_ids = [], []

            for doc in cursor:
                text = doc.get("question", "")
                if not text:
                    continue

                emb = self.model.encode(self.preprocess_text(text)).astype("float32")
                all_embeddings.append(emb)
                all_ids.append(doc["_id"])

            if not all_embeddings:
                continue

            all_embeddings = np.array(all_embeddings).astype("float32")
            dim = all_embeddings.shape[1]

            index = faiss.IndexHNSWFlat(dim, 32)
            index.hnsw.efConstruction = 200
            index.add(all_embeddings)

            faiss.write_index(index, f"{self.INDEX_DIR}/{exam_id}_index.faiss")
            np.save(
                f"{self.INDEX_DIR}/{exam_id}_ids.npy", np.array(all_ids, dtype=object)
            )

            print(f"✅ Saved FAISS index for {exam_id} with {len(all_ids)} questions.")

    def planq_ai(
        self, query, exam_id, subject_id=None, chapter_id=None, top_k=5, messages=[]
    ):
        if subject_id == "":
            subject_id = None
        if chapter_id == "":
            chapter_id = None

        query = self.preprocess_text(query)
        
        history_for_model = []
        for msg in messages:
            # Gemini API expects 'model' for assistant role.
            role = 'model' if msg['role'] == 'ai' or msg['role'] == 'model' else 'user'
            history_for_model.append({'role': role, 'parts': [msg['content']]})

        # If it's the first message in the chat, use RAG
        if not messages:
            results = self.retrieve_hybrid(query, exam_id, subject_id, chapter_id, top_k)
            context = "\n".join(
                [
                    f"Q{i+1}: {r['question']}\nA{i+1}: {r.get('explanation', '')}"
                    for i, r in enumerate(results)
                ]
            )

            prompt = f"""
You are **PlanqAI**, an advanced AI tutor built for Indian students preparing for **entrance exams like JEE, NEET, and other competitive exams**.

🎯 **Your Goals:**
- Provide **accurate, step-by-step explanations** to help students truly understand the concept.
- Use **retrieved context questions (if relevant)** as examples or references.
- If the context is irrelevant or insufficient, rely on your **own knowledge** to answer.
- Keep answers **concise yet complete** – focus on **concept clarity** rather than just giving the final answer.

📌 **Important Instructions:**
1. If the question is **theoretical**, give a **clear explanation with examples**.
2. If the question is **numerical/problem-solving**, provide:
   - **Formulae involved**
   - **Step-by-step solution approach**
   - **Final answer (only if calculable with given data)**
3. If there are **multiple possible approaches**, briefly mention the alternative methods.
4. Use **math formatting (LaTeX style)** for equations when needed.
5. Avoid **unnecessary extra details** – only include what helps the student understand and solve similar questions.

📖 **Context from previous exam questions (can be used as reference):**
{context}

💡 **Student's Question:**
{query}

📝 **Your Response:**
- Begin with a **short direct answer or key concept**.
- Then, give a **step-by-step explanation or derivation** if needed.
- If the context is relevant, mention: _"A similar question appeared in previous exams where..."_ and relate it.

Make sure the tone is **friendly, encouraging, and exam-focused**.
            """
            
            chat_session = self.gemini.start_chat(history=[])
            response = chat_session.send_message(prompt)
            return prompt, {"answer": response.text, "context_used": results}

        # For subsequent messages, continue the conversation without RAG
        else:
            chat_session = self.gemini.start_chat(history=history_for_model)
            response = chat_session.send_message(query)
            return query, {"answer": response.text, "context_used": []}


# Example usage:
# generate_embeddings()
# text = "Two forces P⃗P and Q⃗Q act on a body. One force has magnitude twice that of the other, and the resultant of the two forces is equal to the force of smaller magnitude. The angle between P⃗P and Q⃗Q is cos⁡−1(1m)cos−1(m1​). Find the value of ∣m∣∣m∣."
# text = preprocess_text(text)
# print("Preprocessed Text:", text)
# result = planq_ai(text, exam_id="b3b5a8d8-f409-4e01-8fd4-043d3055db5e", subject_id="7bc04a29-039c-430d-980d-a066b16efc86")
# print("\n💡 AI Answer:\n", result["answer"])
