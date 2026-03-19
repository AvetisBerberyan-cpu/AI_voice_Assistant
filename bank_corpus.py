from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_corpus(path: str) -> str:
    corpus_path = Path(path)
    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Bank corpus not found at {corpus_path}. Run scripts/scrape_banks.py first."
        )
    return corpus_path.read_text(encoding="utf-8")


def load_corpus_json(path: str) -> Dict[str, Any]:
    corpus_path = Path(path)
    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Bank corpus JSON not found at {corpus_path}. Run scripts/scrape_banks.py first."
        )
    return json.loads(corpus_path.read_text(encoding="utf-8"))


TOKEN_RE = re.compile(r"[A-Za-z0-9\u0530-\u058F]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def _chunk_text(text: str, max_chars: int = 1400, overlap: int = 200) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


class RAGIndex:
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self.df: Dict[str, int] = {}
        self.doc_tf: List[Dict[str, int]] = []
        self._build()

    def _build(self) -> None:
        for doc in self.docs:
            tokens = _tokenize(doc["text"])
            tf: Dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            self.doc_tf.append(tf)
            for tok in set(tokens):
                self.df[tok] = self.df.get(tok, 0) + 1

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scores: List[Tuple[int, float]] = []
        n_docs = len(self.docs)
        for idx, tf in enumerate(self.doc_tf):
            score = 0.0
            for tok in q_tokens:
                if tok not in tf:
                    continue
                df = self.df.get(tok, 1)
                idf = math.log((n_docs + 1) / (df + 1)) + 1.0
                score += tf[tok] * idf
            if score > 0:
                scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def build_rag_index(corpus: Dict[str, Any]) -> RAGIndex:
    docs: List[Dict[str, Any]] = []
    for bank in corpus.get("banks", []):
        bank_name = bank.get("name", "")
        bank_slug = bank.get("slug", "")
        for topic, items in bank.get("topics", {}).items():
            for item in items:
                url = item.get("url", "")
                text = item.get("text", "")
                for chunk in _chunk_text(text):
                    docs.append(
                        {
                            "bank": bank_name,
                            "slug": bank_slug,
                            "topic": topic,
                            "url": url,
                            "text": chunk,
                        }
                    )
    return RAGIndex(docs)


def format_top_docs(index: RAGIndex, query: str, top_k: int = 10, max_chars: int = 6000) -> str:
    results = index.search(query, top_k=top_k)
    lines: List[str] = []
    for rank, (idx, score) in enumerate(results, start=1):
        doc = index.docs[idx]
        lines.append(f"[DOC {rank}] bank={doc['bank']} topic={doc['topic']} score={score:.2f}")
        lines.append(f"SOURCE: {doc['url']}")
        lines.append("CONTENT:")
        lines.append(doc["text"])
        lines.append("")
    result = "\n".join(lines).strip()
    if len(result) > max_chars:
        result = result[: max_chars - 20] + "\n[TRUNCATED]\n"
    return result
