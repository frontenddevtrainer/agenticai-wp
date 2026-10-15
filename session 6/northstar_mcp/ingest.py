"""Day 5 Lab 1: build Chroma indexes from docs/ with metadata, at three chunk sizes.

Prereq: ollama pull nomic-embed-text.   Run: python ingest.py
Set CHROMA_HOST/CHROMA_PORT to use a Chroma server (Day 9 compose) instead of ./chroma.
"""
import os
import pathlib
import re

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

DOCS_DIR = pathlib.Path(__file__).parent / "docs"
emb = OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                       base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))


def chroma_kwargs() -> dict:
    if os.getenv("CHROMA_HOST"):
        import chromadb
        return {"client": chromadb.HttpClient(host=os.environ["CHROMA_HOST"], port=int(os.getenv("CHROMA_PORT", "8000")))}
    return {"persist_directory": str(pathlib.Path(__file__).parent / "chroma")}


def load_docs() -> list[Document]:
    out = []
    for p in sorted(DOCS_DIR.glob("*.md")):
        text, meta = p.read_text(), {}
        if m := re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S):
            meta, text = yaml.safe_load(m.group(1)), m.group(2)
        meta = {k: str(v) for k, v in meta.items()}                 # Chroma metadata must be scalar
        meta["is_current"] = "superseded_by" not in meta            # filterable boolean
        meta["effective_year"] = int(meta.get("effective_date", "1970")[:4])
        out.append(Document(text, metadata={"source": p.stem, **meta}))
    return out


def chunk(docs: list[Document], size: int) -> list[Document]:
    md = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "section")], strip_headers=False)
    rec = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=size // 10)
    chunks = []
    for d in docs:
        for sec in md.split_text(d.page_content):                   # structure-aware first...
            sec.metadata |= d.metadata
            chunks += rec.split_documents([sec])                     # ...then size-bounded
    return chunks


def build(size: int) -> Chroma:
    name = f"northstar_{size}"
    vs = Chroma(collection_name=name, embedding_function=emb, collection_metadata={"hnsw:space": "cosine"},
                **chroma_kwargs())
    vs.reset_collection()                                            # idempotent re-ingest
    vs.add_documents(chunk(load_docs(), size))
    return vs


def open_store(size: int = 500) -> Chroma:
    return Chroma(collection_name=f"northstar_{size}", embedding_function=emb,
                  collection_metadata={"hnsw:space": "cosine"}, **chroma_kwargs())


if __name__ == "__main__":
    q = "approvals needed for a 12% limit increase for a High-risk-tier merchant"
    for size in (150, 500, 1500):
        vs = build(size)
        print(f"\n=== chunk size {size}: {vs._collection.count()} chunks ===")
        for doc, score in vs.similarity_search_with_relevance_scores(q, k=3):
            print(f"  {score:.3f} {doc.metadata['source']:38} §{doc.metadata.get('section', '-')[:30]:30} | "
                  f"{doc.page_content[:60]!r}")