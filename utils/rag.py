import os
import pickle
import faiss
import numpy as np
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient
from dotenv import load_dotenv
import json

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_KEY"))
gemini = genai.GenerativeModel("gemini-2.0-flash")

model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")

client = MongoClient("mongodb://localhost:27017")
db = client["pyqs"]
questions_col = db["questions"]

INDEX_DIR = "faiss_indexes"
os.makedirs(INDEX_DIR, exist_ok=True)

def clean_html(text): return BeautifulSoup(text, "html.parser").get_text()
def clean_latex(text): return re.sub(r"\$[^\$]*\$", "", text)
def preprocess_text(text): return clean_latex(clean_html(text)).strip()

# --------------------------------------
# Load FAISS index + metadata per exam
# --------------------------------------
def load_exam_index(exam_id):
    faiss_file = f"{INDEX_DIR}/{exam_id}_index.faiss"
    meta_file = f"{INDEX_DIR}/{exam_id}_meta.pkl"
    emb_file = f"{INDEX_DIR}/{exam_id}_emb.npy"

    if not (os.path.exists(faiss_file) and os.path.exists(meta_file) and os.path.exists(emb_file)):
        return None, None, None

    index = faiss.read_index(faiss_file)
    with open(meta_file, "rb") as f:
        metadata = pickle.load(f)
    embeddings = np.load(emb_file)

    return index, metadata, embeddings

# --------------------------------------
# Hybrid Retrieval (FAISS + BM25)
# --------------------------------------
def retrieve_hybrid(query, exam_id, subject_id=None, chapter_id=None, top_k=5, alpha=0.6):
    index, metadata, embeddings = load_exam_index(exam_id)
    if index is None:
        return []

    query_clean = preprocess_text(query)
    query_emb = model.encode(query_clean).astype("float32").reshape(1, -1)

    D, I = index.search(query_emb, top_k * 10)  # search more, then filter
    results = []
    for idx, dist in zip(I[0], D[0]):
        meta = metadata[idx]
        if subject_id and meta["subject"] != subject_id:
            continue
        if chapter_id and meta["chapter"] != chapter_id:
            continue
        results.append((meta, 1 - dist))  # similarity = 1 - L2 distance

    if not results:
        return []

    tokenized_corpus = [r[0]["clean_text"].split() for r in results]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query_clean.split())

    sims = np.array([r[1] for r in results])
    bm25_norm = (bm25_scores - bm25_scores.min()) / (np.ptp(bm25_scores) + 1e-6)

    hybrid_scores = alpha * sims + (1 - alpha) * bm25_norm
    ranked = sorted(zip(results, hybrid_scores), key=lambda x: x[1], reverse=True)
    
    result = []
    
    for r, s in ranked[:top_k]:
        ques = questions_col.find_one({"_id": r[0]["_id"]}, {"explanation": 1})
        result.append({"question": r[0]["raw_question"], "score": round(s, 4), "explanation": ques.get("explanation")})

    return result

# --------------------------------------
# Generate + Store Embeddings (Sharded)
# --------------------------------------
def generate_embeddings(batch_size=64):
    exams = questions_col.distinct("exam")

    for exam_id in exams:
        cursor = questions_col.find({"exam": exam_id}, {"_id": 1, "question": 1, "subject": 1, "chapter": 1, "level": 1})

        all_embeddings, all_metadata = [], []
        for doc in cursor:
            text = doc.get("question", "")
            if not text:
                continue

            clean_text = preprocess_text(text)
            emb = model.encode(clean_text).astype("float32")

            all_embeddings.append(emb)
            all_metadata.append({
                "_id": doc["_id"],
                "raw_question": text,
                "clean_text": clean_text,
                "exam": exam_id,
                "subject": doc.get("subject"),
                "chapter": doc.get("chapter"),
                "level": doc.get("level", 2)
            })

        if not all_embeddings:
            continue

        all_embeddings = np.array(all_embeddings).astype("float32")

        dim = all_embeddings.shape[1]
        index = faiss.IndexHNSWFlat(dim, 32)
        index.hnsw.efConstruction = 200
        index.add(all_embeddings)

        # Save per exam
        faiss.write_index(index, f"{INDEX_DIR}/{exam_id}_index.faiss")
        np.save(f"{INDEX_DIR}/{exam_id}_emb.npy", all_embeddings)
        with open(f"{INDEX_DIR}/{exam_id}_meta.pkl", "wb") as f:
            pickle.dump(all_metadata, f)

        print(f"✅ Saved {len(all_metadata)} embeddings for exam {exam_id}")

# --------------------------------------
# PlanqAI wrapper
# --------------------------------------
def planq_ai(query, exam_id, subject_id=None, chapter_id=None, top_k=5):
    results = retrieve_hybrid(query, exam_id, subject_id, chapter_id, top_k)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    context = ""
    for i, r in enumerate(results):
        context += f"Q{i+1}: {r['question']}\n"
        if r.get("explanation"):
            context += f"A{i+1}: {r['explanation']}\n\n"

    prompt = f"""
    You are PlanqAI, an AI tutor for entrance exam students in India.
    Use the following context from previous exam questions to answer the query.

    Context:
    {context}

    Question:
    {query}

    Provide a helpful, concise explanation with examples if needed.
    """

    response = gemini.generate_content(prompt)
    return {"answer": response.text, "context_used": results}

if __name__ == "__main__":
    # generate_embeddings()
    text = "Two forces P⃗P and Q⃗Q act on a body. One force has magnitude twice that of the other, and the resultant of the two forces is equal to the force of smaller magnitude. The angle between P⃗P and Q⃗Q is cos⁡−1(1m)cos−1(m1​). Find the value of ∣m∣∣m∣."
    text = preprocess_text(text)
    print("Preprocessed Text:", text)
    result = planq_ai(text, exam_id="b3b5a8d8-f409-4e01-8fd4-043d3055db5e", subject_id="7bc04a29-039c-430d-980d-a066b16efc86")
    print("\n💡 AI Answer:\n", result["answer"])
