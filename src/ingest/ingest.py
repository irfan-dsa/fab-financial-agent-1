# src/ingest/ingest.py
import json
import logging
import os
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from parsers.pdf_parser import (chunks_to_dataframe, parse_pdf_to_chunks,
                                save_chunks_to_json)
from vectorstore.qdrant_store import (create_collection_if_not_exists,
                                      get_client, upsert_chunks)

# Load environment variables (prefer config/.env over config/.env.sample)
env_path = Path("config") / ".env"
if not env_path.exists():
    env_path = Path("config") / ".env.sample"
load_dotenv(env_path)

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
BATCH_SIZE = int(os.getenv("EMB_BATCH_SIZE", 64))

logger = logging.getLogger("ingest")
logging.basicConfig(level=logging.INFO)

# Cache model to avoid reloading
_model: SentenceTransformer | None = None


def get_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model %s", model_name)
        _model = SentenceTransformer(model_name)
    return _model


def embed_texts_batched(
    texts: List[str], batch_size: int = BATCH_SIZE, model_name: str = MODEL_NAME
):
    """
    Yield embeddings in batches as lists of floats.
    """
    model = get_model(model_name)
    n = len(texts)
    embeddings: List[List[float]] = []
    for i in range(0, n, batch_size):
        batch = texts[i : i + batch_size]
        embs = model.encode(batch, show_progress_bar=False, convert_to_numpy=True)
        # convert to python lists
        for vec in embs:
            embeddings.append(vec.tolist())
    return embeddings


def ingest_pdf(filepath: str, push_to_qdrant: bool = True, out_dir: str = "data/out"):
    p = Path(filepath)
    logger.info("Parsing PDF: %s", p)
    chunks = parse_pdf_to_chunks(str(p))

    # Save raw chunks JSON
    out_json = Path(out_dir) / f"{p.stem}_chunks.json"
    save_chunks_to_json(chunks, str(out_json))

    # Prepare texts, ids and metadata
    texts = [c["text"] or "" for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [
        {
            "file": c["file"],
            "page": c["page"],
            "section": c["section"],
            "chunk_type": c["chunk_type"],
            "chunk_id": c["id"],
        }
        for c in chunks
    ]

    if push_to_qdrant:
        client = get_client()
        if not texts:
            logger.warning("No text chunks found for %s", p)
        else:
            logger.info(
                "Computing embeddings for %d chunks (batch=%d)", len(texts), BATCH_SIZE
            )
            embeddings = embed_texts_batched(texts, batch_size=BATCH_SIZE)
            # ensure collection exists with correct vector size
            if embeddings:
                create_collection_if_not_exists(client, vector_size=len(embeddings[0]))
                upsert_chunks(client, embeddings, metadatas, ids)
                logger.info("Upserted %d vectors to Qdrant collection", len(embeddings))
    return {"chunks_path": str(out_json), "num_chunks": len(chunks)}
