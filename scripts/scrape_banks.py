#!/usr/bin/env python3
import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
import yaml
from bs4 import BeautifulSoup
from pypdf import PdfReader

TOPICS = {"credits", "deposits", "branches"}
ARMENIAN_RE = re.compile(r"[\u0530-\u058F]")


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def filter_armenian(text: str) -> str:
    if not text:
        return text
    if not ARMENIAN_RE.search(text):
        return text
    parts = re.split(r"(?<=[\.\!\?\։\:])\s+", text)
    armenian_parts = [p for p in parts if ARMENIAN_RE.search(p)]
    return " ".join(armenian_parts).strip()


def extract_text_from_html(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = normalize_text(text)
    text = filter_armenian(text)
    return text


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    text = normalize_text("\n".join(pages))
    return filter_armenian(text)


def fetch_url(url: str, *, user_agent: str | None = None, render_js: bool = False) -> Dict[str, Any]:
    if render_js:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required for --render-js. Install with `pip install playwright` "
                "and run `playwright install`."
            ) from exc
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            html = page.content()
            browser.close()
        return {"url": url, "content_type": "text/html; charset=utf-8", "content": html.encode("utf-8")}
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    resp = requests.get(url, timeout=40, headers=headers)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "").lower()
    return {"url": url, "content_type": content_type, "content": resp.content}

def load_local(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Local file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        content_type = "application/pdf"
    elif suffix in {".html", ".htm"}:
        content_type = "text/html"
    else:
        content_type = "application/octet-stream"
    return {"url": str(path), "content_type": content_type, "content": path.read_bytes()}

def extract_text(payload: Dict[str, Any]) -> str:
    content_type = payload["content_type"]
    content = payload["content"]
    if "pdf" in content_type or payload["url"].lower().endswith(".pdf"):
        return extract_text_from_pdf(content)
    return extract_text_from_html(content)


def load_config(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data or "banks" not in data:
        raise ValueError("banks.yaml must include a top-level 'banks' list")
    return data


def build_corpus(
    config: Dict[str, Any],
    *,
    skip_errors: bool,
    user_agent: str | None,
    base_dir: Path,
    render_js: bool,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    banks_out: List[Dict[str, Any]] = []
    for bank in config["banks"]:
        bank_name = bank["name"]
        bank_slug = bank.get("slug", bank_name.lower().replace(" ", "-"))
        sources = bank.get("sources", {})
        bank_entry = {
            "name": bank_name,
            "slug": bank_slug,
            "topics": {},
        }
        for topic, items in sources.items():
            if topic not in TOPICS:
                raise ValueError(f"Unknown topic '{topic}' for bank {bank_name}")
            bank_entry["topics"][topic] = []
            for item in items:
                url = item.get("url")
                local_path = item.get("path")
                note = item.get("note")
                try:
                    if local_path:
                        payload = load_local(base_dir / local_path)
                    elif url:
                        payload = fetch_url(url, user_agent=user_agent, render_js=render_js)
                    else:
                        raise ValueError("Source item must include either 'url' or 'path'")
                    text = extract_text(payload)
                    bank_entry["topics"][topic].append(
                        {
                            "url": url or str(base_dir / local_path),
                            "note": note,
                            "content_type": payload["content_type"],
                            "text": text,
                            "scraped_at": now,
                        }
                    )
                except Exception as exc:
                    if not skip_errors:
                        raise
                    print(f"[warn] Failed to fetch {url}: {exc}")
        banks_out.append(bank_entry)

    return {"generated_at": now, "banks": banks_out}


def render_corpus_text(corpus: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"SCRAPED_AT: {corpus['generated_at']}")
    lines.append("TOPICS: credits | deposits | branches")
    for bank in corpus["banks"]:
        lines.append("")
        lines.append(f"=== BANK: {bank['name']} ===")
        for topic, items in bank["topics"].items():
            lines.append("")
            lines.append(f"--- TOPIC: {topic} ---")
            for item in items:
                lines.append(f"SOURCE: {item['url']}")
                if item.get("note"):
                    lines.append(f"NOTE: {item['note']}")
                lines.append("CONTENT:")
                lines.append(item["text"])
                lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Armenian bank websites for credits, deposits, and branches.")
    parser.add_argument("--config", default="banks.yaml", help="Path to banks.yaml")
    parser.add_argument("--out-text", default="data/banks_corpus.txt", help="Output text corpus")
    parser.add_argument("--out-json", default="data/banks_corpus.json", help="Output JSON corpus")
    parser.add_argument("--skip-errors", action="store_true", help="Skip URLs that fail to fetch")
    parser.add_argument("--render-js", action="store_true", help="Render JavaScript pages with Playwright")
    parser.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        help="User-Agent header for HTTP requests",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    corpus = build_corpus(
        load_config(config_path),
        skip_errors=args.skip_errors,
        user_agent=args.user_agent,
        base_dir=config_path.parent,
        render_js=args.render_js,
    )

    out_text = Path(args.out_text)
    out_json = Path(args.out_json)
    out_text.parent.mkdir(parents=True, exist_ok=True)

    out_text.write_text(render_corpus_text(corpus), encoding="utf-8")
    out_json.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {out_text} and {out_json}")


if __name__ == "__main__":
    main()
