"""Credit & Compliance Policy RAG — hybrid pgvector search over RBI Master Directions,
internal credit policy manual, and AML/KYC guidelines. Grounds the MSME Risk & Cash-Flow
Agent's reasoning in actual policy text instead of the model's own unverified recall."""
import hashlib

from shared.database import AsyncSessionLocal
from shared.llm import complete, SONNET


async def embed_query(text: str) -> list[float]:
    """Bedrock Titan V2 embedding (1536-dim). Placeholder hash-based vector for dev/test."""
    h = int(hashlib.md5(text.encode()).hexdigest(), 16)
    vec = [0.0] * 1536
    vec[h % 1536] = 1.0
    return vec


async def hybrid_search(question: str, top_k: int = 5) -> list[dict]:
    """
    Dense (pgvector HNSW cosine) + sparse (Postgres tsvector/BM25-style) search run in
    parallel, combined via Reciprocal Rank Fusion. Returns the top_k policy chunks.
    """
    from sqlalchemy import text as sql

    embedding = await embed_query(question)

    async with AsyncSessionLocal() as db:
        dense = await db.execute(
            sql(
                "SELECT id, chunk_text, source_ref, source_type, "
                "1 - (embedding <=> :emb::vector) AS score "
                "FROM credit_policy_chunks ORDER BY embedding <=> :emb::vector LIMIT :k"
            ),
            {"emb": str(embedding), "k": top_k},
        )
        sparse = await db.execute(
            sql(
                "SELECT id, chunk_text, source_ref, source_type, "
                "ts_rank(chunk_tsv, plainto_tsquery('english', :q)) AS score "
                "FROM credit_policy_chunks WHERE chunk_tsv @@ plainto_tsquery('english', :q) "
                "ORDER BY score DESC LIMIT :k"
            ),
            {"q": question, "k": top_k},
        )

    ranked: dict[int, float] = {}
    rows_by_id: dict[int, dict] = {}
    for rank, row in enumerate(dense.fetchall()):
        ranked[row.id] = ranked.get(row.id, 0) + 1 / (60 + rank)
        rows_by_id[row.id] = row._asdict()
    for rank, row in enumerate(sparse.fetchall()):
        ranked[row.id] = ranked.get(row.id, 0) + 1 / (60 + rank)
        rows_by_id.setdefault(row.id, row._asdict())

    top_ids = sorted(ranked, key=ranked.get, reverse=True)[:top_k]
    return [rows_by_id[i] for i in top_ids]


async def policy_qa(question: str) -> tuple[str, list[str]]:
    """
    Answers a credit/compliance policy question grounded in RBI Master Directions,
    the internal credit policy manual, and KYC/AML guidelines.
    Returns (answer_text, [source_refs]).
    """
    chunks = await hybrid_search(question)
    if not chunks:
        return "No relevant policy found.", []

    context = "\n\n---\n\n".join(f"[{c['source_type']}] {c['chunk_text']}" for c in chunks)
    refs = [c["source_ref"] for c in chunks]

    answer = await complete(
        messages=[{"role": "user", "content": f"Question: {question}\n\nPolicy context:\n{context}"}],
        system=(
            "You are a credit and compliance policy assistant for Ai-ME BANK. Answer based "
            "only on the provided policy context (RBI Master Directions, internal credit "
            "policy, KYC/AML guidelines). Be concise and cite which source informed your answer."
        ),
        model=SONNET,
        max_tokens=512,
        trace_name="credit_policy_qa",
    )
    return answer, refs
