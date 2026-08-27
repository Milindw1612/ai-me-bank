# -*- coding: utf-8 -*-
"""
Ingests the 13 synthetic policy PDFs into 3 Hybrid RAG collections
(loan_policies, hr_policies, general_policies):
  - Structure-aware chunking: split by the numbered section headings
    already baked into each PDF (1. Heading, 2. Heading, ...).
  - Dense index: Chroma (persistent, local), embeddings via
    BAAI/bge-base-en-v1.5 (local, offline after first download).
  - Sparse index: rank_bm25 (BM25Okapi), pickled alongside Chroma so
    the server can load both without re-parsing PDFs at runtime.

Run: python ingest.py
Output: chroma_db/ (persistent Chroma store), bm25_indexes.pkl
"""
import glob
import os
import pickle
import re

import chromadb
import pdfplumber
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

COLLECTIONS = {
    "loan_policies": "loan",
    "fraud_policies": "fraud",
}

HEADING_RE = re.compile(r"^\d+\.\s+.+$")
META_RE = re.compile(
    r"Document Code:\s*([\w-]+).*?Version:\s*([\d.]+).*?"
    r"Effective Date:\s*([\d-]+\w*(?:-\w+)?-\d+).*?Status:\s*(\w+)"
)

DB_DIR = "chroma_db"
BM25_PATH = "bm25_indexes.pkl"


def extract_doc(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text


def parse_doc(text, filename):
    lines = text.split("\n")
    title = lines[1].strip() if len(lines) > 1 else filename
    meta_line = " ".join(lines[:4])
    m = META_RE.search(meta_line.replace(" ", " "))
    if m:
        doc_code, version, effective_date, status = m.groups()
    else:
        doc_code, version, effective_date, status = filename, "1.0", "unknown", "Active"

    chunks = []
    current_heading = None
    current_lines = []

    def flush():
        if current_heading and current_lines:
            body = " ".join(current_lines).strip()
            if body:
                chunks.append({"heading": current_heading, "text": body})

    for line in lines[3:]:
        line = line.strip()
        if not line:
            continue
        if HEADING_RE.match(line):
            flush()
            current_heading = line
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    return {
        "doc_code": doc_code,
        "title": title,
        "version": version,
        "effective_date": effective_date,
        "status": status,
        "chunks": chunks,
    }


def simple_tokenize(text):
    return re.findall(r"[a-z0-9.]+", text.lower())


def main():
    print("Loading embedding model (BAAI/bge-base-en-v1.5, local)...")
    embedder = SentenceTransformer("BAAI/bge-base-en-v1.5")

    client = chromadb.PersistentClient(path=DB_DIR)
    bm25_data = {}  # collection_name -> {"bm25": BM25Okapi, "chunks": [...], "ids": [...]}

    for collection_name, folder in COLLECTIONS.items():
        print(f"\n=== {collection_name} ({folder}/) ===")
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        collection = client.create_collection(collection_name)

        all_chunk_texts = []
        all_ids = []
        all_metadatas = []
        all_embed_inputs = []

        pdf_files = sorted(glob.glob(f"{folder}/*.pdf"))
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            text = extract_doc(pdf_path)
            doc = parse_doc(text, filename)
            print(f"  {filename}: {len(doc['chunks'])} chunks "
                  f"(code={doc['doc_code']}, version={doc['version']}, status={doc['status']})")

            for i, chunk in enumerate(doc["chunks"]):
                chunk_id = f"{doc['doc_code']}-{i+1}"
                clause_num = chunk["heading"].split(".", 1)[0]
                metadata = {
                    "doc_code": doc["doc_code"],
                    "doc_title": doc["title"],
                    "version": doc["version"],
                    "effective_date": doc["effective_date"],
                    "status": doc["status"],
                    "clause": clause_num,
                    "heading": chunk["heading"],
                    "source_file": filename,
                }
                # Prefix with doc title + heading so embeddings capture context,
                # not just the bare clause body.
                embed_text = f"{doc['title']} - {chunk['heading']}\n{chunk['text']}"

                all_ids.append(chunk_id)
                all_metadatas.append(metadata)
                all_chunk_texts.append(chunk["text"])
                all_embed_inputs.append(embed_text)

        if not all_ids:
            print(f"  WARNING: no chunks found for {collection_name}")
            continue

        print(f"  Embedding {len(all_embed_inputs)} chunks...")
        embeddings = embedder.encode(all_embed_inputs, show_progress_bar=False, normalize_embeddings=True)

        collection.add(
            ids=all_ids,
            embeddings=embeddings.tolist(),
            documents=all_chunk_texts,
            metadatas=all_metadatas,
        )

        tokenized = [simple_tokenize(t) for t in all_embed_inputs]
        bm25 = BM25Okapi(tokenized)
        bm25_data[collection_name] = {
            "bm25": bm25,
            "chunks": all_chunk_texts,
            "ids": all_ids,
            "metadatas": all_metadatas,
        }
        print(f"  Indexed {len(all_ids)} chunks into Chroma + BM25 for '{collection_name}'.")

    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    print(f"\nDone. Chroma store: {DB_DIR}/  BM25 indexes: {BM25_PATH}")


if __name__ == "__main__":
    main()
