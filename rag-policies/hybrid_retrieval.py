# -*- coding: utf-8 -*-
"""
Hybrid RAG retrieval: dense (Chroma/bge-base-en-v1.5) + sparse (BM25),
merged via Reciprocal Rank Fusion (RRF). Matches the pattern already
described in the site's own architecture.html ("hybrid pgvector + BM25 -
RRF"), just running on local Chroma instead of AWS RDS+pgvector.
"""
import pickle
import re

import chromadb
from sentence_transformers import SentenceTransformer

DB_DIR = "chroma_db"
BM25_PATH = "bm25_indexes.pkl"
RRF_K = 60  # standard RRF damping constant


def simple_tokenize(text):
    return re.findall(r"[a-z0-9.]+", text.lower())


class HybridRetriever:
    def __init__(self):
        self.embedder = SentenceTransformer("BAAI/bge-base-en-v1.5")
        self.client = chromadb.PersistentClient(path=DB_DIR)
        with open(BM25_PATH, "rb") as f:
            self.bm25_data = pickle.load(f)

    def dense_top_distance(self, query, collection_name):
        """Returns the top-1 dense (Chroma) distance for this query
        against this collection -- comparable ACROSS collections
        (unlike RRF scores, which are only meaningful within a single
        collection's own rank positions). Smaller = closer match.
        Used for routing; the actual retrieval still uses full hybrid
        search once a collection is chosen."""
        data = self.bm25_data.get(collection_name)
        if not data:
            return float("inf")
        query_emb = self.embedder.encode([query], normalize_embeddings=True)[0].tolist()
        collection = self.client.get_collection(collection_name)
        result = collection.query(query_embeddings=[query_emb], n_results=1)
        distances = result.get("distances", [[]])[0]
        return distances[0] if distances else float("inf")

    def retrieve(self, query, collection_name, top_k=4):
        data = self.bm25_data.get(collection_name)
        if not data:
            return []

        # --- Dense (vector) search ---
        query_emb = self.embedder.encode([query], normalize_embeddings=True)[0].tolist()
        collection = self.client.get_collection(collection_name)
        dense_result = collection.query(query_embeddings=[query_emb], n_results=min(10, len(data["ids"])))
        dense_ids = dense_result["ids"][0]  # ranked list, best first

        # --- Sparse (BM25) search ---
        tokenized_query = simple_tokenize(query)
        bm25_scores = data["bm25"].get_scores(tokenized_query)
        ranked_sparse = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
        sparse_ids = [data["ids"][i] for i in ranked_sparse[:10]]

        # --- Reciprocal Rank Fusion ---
        rrf_scores = {}
        for rank, doc_id in enumerate(dense_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (RRF_K + rank + 1)
        for rank, doc_id in enumerate(sparse_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (RRF_K + rank + 1)

        fused = sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        id_to_idx = {doc_id: i for i, doc_id in enumerate(data["ids"])}
        results = []
        for doc_id, score in fused:
            idx = id_to_idx[doc_id]
            results.append({
                "id": doc_id,
                "rrf_score": score,
                "text": data["chunks"][idx],
                "metadata": data["metadatas"][idx],
            })
        return results


if __name__ == "__main__":
    retriever = HybridRetriever()
    test_queries = [
        ("loan_policies", "What is the maximum FOIR for self-employed applicants?"),
        ("loan_policies", "How many days do I have to submit missing loan documents?"),
        ("hr_policies", "How many sick leave days do employees get?"),
        ("hr_policies", "What is the maximum number of work from home days per month?"),
        ("general_policies", "What is the approval threshold for a purchase order?"),
    ]
    for collection, query in test_queries:
        print(f"\n=== [{collection}] Query: {query!r} ===")
        results = retriever.retrieve(query, collection, top_k=3)
        for r in results:
            print(f"  [{r['metadata']['doc_code']} clause {r['metadata']['clause']}] "
                  f"RRF={r['rrf_score']:.4f} | {r['metadata']['heading']}")
            print(f"    {r['text'][:140]}...")
