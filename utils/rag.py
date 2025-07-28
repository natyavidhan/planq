import os
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

# ------------------------------
# Load FAISS Index + ID Mapping
# ------------------------------
def load_exam_index(exam_id):
    faiss_file = f"{INDEX_DIR}/{exam_id}_index.faiss"
    ids_file = f"{INDEX_DIR}/{exam_id}_ids.npy"

    if not (os.path.exists(faiss_file) and os.path.exists(ids_file)):
        return None, None

    index = faiss.read_index(faiss_file)
    ids = np.load(ids_file, allow_pickle=True)  # array of MongoDB IDs

    return index, ids


# ------------------------------
# Hybrid Retrieval (FAISS + BM25)
# ------------------------------
def retrieve_hybrid(query, exam_id, subject_id=None, chapter_id=None, top_k=5, alpha=0.6):
    index, ids = load_exam_index(exam_id)
    if index is None:
        return []

    query_clean = preprocess_text(query)
    query_emb = model.encode(query_clean).astype("float32").reshape(1, -1)

    D, I = index.search(query_emb, top_k * 20)  # get more, then filter
    results = []

    for idx, dist in zip(I[0], D[0]):
        q_id = ids[idx]
        meta = questions_col.find_one(
            {"_id": q_id},
            {"question": 1, "subject": 1, "chapter": 1, "explanation": 1}
        )
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
    bm25_scores = bm25.get_scores(query_clean.split())

    sims = np.array([r[1] for r in results])
    bm25_norm = (bm25_scores - bm25_scores.min()) / (np.ptp(bm25_scores) + 1e-6)

    hybrid_scores = alpha * sims + (1 - alpha) * bm25_norm
    ranked = sorted(zip(results, hybrid_scores), key=lambda x: x[1], reverse=True)

    return [
        {"question": r[0]["question"], "score": round(s, 4), "explanation": r[0].get("explanation")}
        for r, s in ranked[:top_k]
    ]


# ------------------------------
# Generate + Store FAISS Index
# ------------------------------
def generate_embeddings(batch_size=64):
    exams = [
        "b3b5a8d8-f409-4e01-8fd4-043d3055db5e", # JEE Main
        "f3e78517-c050-4fea-822b-e43c4d2d3523", # WBJEE
        "4625ad6f-33db-4c22-96e0-6c23830482de", # NEET
        "c8da26c7-cf1b-421f-829b-c95dbdd3cc6a", # BITSAT
    ]

    for exam_id in exams:
        cursor = questions_col.find(
            {"exam": exam_id},
            {"_id": 1, "question": 1}
        )

        all_embeddings, all_ids = [], []

        for doc in cursor:
            text = doc.get("question", "")
            if not text:
                continue

            emb = model.encode(preprocess_text(text)).astype("float32")
            all_embeddings.append(emb)
            all_ids.append(doc["_id"])

        if not all_embeddings:
            continue

        all_embeddings = np.array(all_embeddings).astype("float32")
        dim = all_embeddings.shape[1]

        # ✅ Use IVF+PQ (much smaller size)
        nlist = 50  # number of clusters
        m = 16      # number of sub-vectors
        nbits = 8   # bits per sub-vector

        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, nbits)

        index.train(all_embeddings)
        index.add(all_embeddings)

        # Save FAISS index and ID mapping
        faiss.write_index(index, f"{INDEX_DIR}/{exam_id}_index.faiss")
        np.save(f"{INDEX_DIR}/{exam_id}_ids.npy", np.array(all_ids, dtype=object))

        print(f"✅ Saved FAISS index for {exam_id} with {len(all_ids)} questions.")


# ------------------------------
# PlanqAI Wrapper
# ------------------------------
def planq_ai(query, exam_id, subject_id=None, chapter_id=None, top_k=5):
    results = retrieve_hybrid(query, exam_id, subject_id, chapter_id, top_k)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    context = "\n".join([f"Q{i+1}: {r['question']}\nA{i+1}: {r.get('explanation', '')}" for i, r in enumerate(results)])

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
