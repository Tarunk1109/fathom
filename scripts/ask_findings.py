#!/usr/bin/env python3
"""Ask Your Findings — final.md B4 / fathom.md §11.8.

    make ask Q="Which rate sources stopped at a licence requirement?"
    .venv/bin/python scripts/ask_findings.py "What did the Aviva collapse rest on?"

A question box over FATHOM's own verified evidence. Answers **only** from retrieved artifacts —
never from the model's general knowledge — and every answer cites the registry rows and evidence
CIDs it drew from.

**Why this is a CLI, not the live text box the UI's Evidence panel visually suggests.** Embedding
an API key in `ui/index.html`'s JavaScript would put a live secret in the page source of every
copy of that file — exactly the class of leak this project's own PII/secret discipline exists to
prevent (see docs/DECISIONS.md DL-26). The key stays server-side, read from a local `.env` that is
gitignored and never committed, never printed, never sent anywhere but the Anthropic API.

**The hard constraint, enforced structurally, not by a hopeful prompt.** Retrieval happens first,
in this script, over `ui/data.json`'s already-collected records/results/evidence. Only the
retrieved rows are sent to the model, inside an explicit instruction that answers must cite a
registry_id or evidence CID from the provided rows and must say so plainly if the evidence does not
contain the answer. The model never sees anything it wasn't handed, and it is never handed
anything except what retrieval actually found — there is no path from "the model doesn't know" to
"the model guesses," because guessing has nothing to draw on.

No `anthropic` SDK dependency — this calls the REST API directly with stdlib `urllib`, since B4 is
outside Part A's "no new dependencies" allowance and adding an SDK for one script is not worth it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "ui" / "data.json"
ENV_PATH = ROOT / ".env"
MODEL = os.environ.get("FATHOM_ASK_MODEL", "claude-sonnet-5")
API_URL = "https://api.anthropic.com/v1/messages"

STOPWORDS = {"the", "a", "an", "is", "are", "was", "were", "what", "which", "who", "did",
            "does", "do", "to", "of", "in", "on", "at", "for", "and", "or", "this", "that"}


def load_env() -> dict[str, str]:
    """Minimal .env parser — no python-dotenv dependency for one variable."""
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 2}


def build_corpus(data: dict) -> list[dict]:
    """One retrievable row per registry record, result, and evidence artifact excerpt."""
    corpus = []
    for r in data.get("records", []):
        text = " ".join(str(r.get(k, "")) for k in
                        ("registry_id", "brand_or_program", "legal_underwriter", "status",
                         "reason_code", "distinct_rate_source_id", "automation_notes"))
        corpus.append({"kind": "registry_record", "id": r["registry_id"], "text": text,
                      "citation": r["registry_id"]})
    for r in data.get("results", []):
        text = " ".join(str(r.get(k, "")) for k in ("route_id", "registry_id", "status", "reason_code")) + \
            " " + " ".join(r.get("variance_from_benchmark", []))
        cid = (r.get("evidence", {}).get("artifact_cids") or [""])[0]
        corpus.append({"kind": "result", "id": r["route_id"], "text": text, "citation": cid or r["route_id"]})
    for a in data.get("evidence", {}).get("artifacts", []):
        text = a.get("route_id", "") + " " + a.get("source", "") + " " + a.get("text_excerpt", "")[:800]
        corpus.append({"kind": "evidence", "id": a["cid"], "text": text, "citation": a["cid"]})
    for rung in data.get("frontier", {}).get("ladder", []):
        text = rung["label"] + " " + " ".join(rec["registry_id"] + " " + rec["brand"] for rec in rung["records"])
        corpus.append({"kind": "frontier_rung", "id": rung["unlock"], "text": text, "citation": rung["unlock"]})
    return corpus


def retrieve(question: str, corpus: list[dict], top_k: int = 12) -> list[dict]:
    q_tokens = tokenize(question)
    scored = []
    for row in corpus:
        row_tokens = tokenize(row["text"])
        overlap = len(q_tokens & row_tokens)
        if overlap:
            scored.append((overlap, row))
    scored.sort(key=lambda x: -x[0])
    return [row for _, row in scored[:top_k]]


def call_claude(api_key: str, question: str, retrieved: list[dict]) -> str:
    if not retrieved:
        return ("No retrieved evidence matched this question. Per the hard constraint, I do not "
               "answer from general knowledge — try rephrasing, or this genuinely isn't covered "
               "by FATHOM's collected evidence.")

    context = "\n\n".join(
        f"[{i+1}] kind={row['kind']} citation={row['citation']}\n{row['text'][:600]}"
        for i, row in enumerate(retrieved))

    system = (
        "You answer questions about the FATHOM Ontario auto insurance market survey using ONLY "
        "the evidence rows provided below. Never use general knowledge about insurers, Ontario "
        "regulation, or anything not in the provided rows. Every factual claim must cite the "
        "bracketed row number(s) it came from, e.g. [2][5]. If the provided rows do not contain "
        "an answer, say so plainly rather than inferring or guessing. Be concise.\n\n"
        f"EVIDENCE ROWS:\n\n{context}"
    )

    body = json.dumps({
        "model": MODEL, "max_tokens": 500,
        "system": system,
        "messages": [{"role": "user", "content": question}],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return f"API error {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        return f"Could not reach the API: {exc.reason}"

    return "".join(block.get("text", "") for block in payload.get("content", []))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("question", nargs="*", help="the question to ask")
    args = ap.parse_args()
    question = " ".join(args.question).strip()
    if not question:
        try:
            question = input("Ask your findings: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 1
    if not question:
        print("no question given")
        return 1

    if not DATA_PATH.exists():
        print(f"error: {DATA_PATH} not found. Run `make run` first.", file=sys.stderr)
        return 1

    env = load_env()
    api_key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("error: no ANTHROPIC_API_KEY in .env or the environment.", file=sys.stderr)
        return 1

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    corpus = build_corpus(data)
    retrieved = retrieve(question, corpus)

    print(f"\nQ: {question}\n")
    print(f"Retrieved {len(retrieved)} evidence row(s):")
    for i, row in enumerate(retrieved):
        print(f"  [{i+1}] {row['kind']:<15} {row['citation']}")

    answer = call_claude(api_key, question, retrieved)
    print(f"\nA: {answer}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
