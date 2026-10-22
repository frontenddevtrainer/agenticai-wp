"""Runs INSIDE the sandbox container (deploy/Dockerfile.evidence-parser). Extracts text from an evidence file.

Usage (in container): python evidence_parser.py /in/evidence      -> JSON on stdout (no writable mounts needed)
"""
import json
import sys


def extract(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(5)
    if head == b"%PDF-":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    return open(path, encoding="utf-8", errors="replace").read()


if __name__ == "__main__":
    json.dump({"text": extract(sys.argv[1])[:50_000]}, sys.stdout)