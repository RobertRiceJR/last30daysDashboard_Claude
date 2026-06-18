"""Cheap 3-judge quality scorer for a run's digest (an LLM-as-judge panel).

Three specialized judges, each a cheap Haiku sub-agent owning one axis, run
once per run (3 calls total) over the whole digest:

  1. Relevance     - are the bullets on-topic and substantive vs. noise?
  2. Faithfulness  - do the cited links match the run's REAL evidence URLs
                     (no fabricated/unsupported citations)?  -- the QE trust gate
  3. Actionability - are the verdicts sound and "what changed / why it matters" useful?

Each returns {"score": 0-100, "issues": [...]}. Composite = weighted mean
(faithfulness weighted highest). Pure stdlib + the `claude` CLI; no API key.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

JUDGE_MODEL = "haiku"  # cheap model alias
_DIRECTIVE = "Read the rubric and material below, then output ONLY the requested JSON object. No prose."

# Faithfulness weighted highest — a hallucinated citation is the worst failure.
WEIGHTS = {"relevance": 0.3, "faithfulness": 0.4, "actionability": 0.3}

_RUBRICS = {
    "relevance": (
        "You are the RELEVANCE judge for a daily research digest. Score 0-100 how on-topic and "
        "substantive the bullets are: high = directly about the stated topics with real signal; "
        "low = off-topic, generic, or keyword-trap noise. "
        'Output JSON only: {"score": <int 0-100>, "issues": ["short note", ...]}.'
    ),
    "faithfulness": (
        "You are the FAITHFULNESS judge. You receive the digest bullets AND the list of REAL evidence "
        "URLs gathered for this run. Score 0-100 how well the bullets' cited links match that evidence "
        "set and avoid fabricated/unsupported citations: 100 = every cited link appears in the evidence "
        "URLs; deduct for any cited link NOT in the set, or any claim with no citation. Put each "
        "fabricated/unmatched link in issues. "
        'Output JSON only: {"score": <int 0-100>, "issues": ["the bad link/claim", ...]}.'
    ),
    "actionability": (
        "You are the ACTIONABILITY judge for a busy executive. Score 0-100 how useful the bullets are: "
        "is 'what changed / why it matters' clear, and are the Act / Ignore / Watch verdicts sensible "
        "given the content? "
        'Output JSON only: {"score": <int 0-100>, "issues": ["short note", ...]}.'
    ),
}


def _run_claude(body: str, timeout: int = 150) -> str:
    claude = shutil.which("claude")
    if not claude:
        return ""
    cmd = [claude, "-p", _DIRECTIVE, "--model", JUDGE_MODEL, "--output-format", "text"]
    if claude.lower().endswith((".cmd", ".bat")):
        cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c"] + cmd
    try:
        proc = subprocess.run(
            cmd, input=body, text=True, capture_output=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return (proc.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _extract_json(text: str) -> dict | None:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start : i + 1])
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _gather(date: str) -> tuple[str, list[str]]:
    """Collect the run's synthesized bullets + the real evidence URLs from raw/<date>/."""
    raw_dir = RAW / date
    bullets, urls = [], set()
    for syn in sorted(raw_dir.glob("*-synthesis.md")):
        topic = syn.stem.replace("-synthesis", "").replace("-", " ")
        bullets.append(f"## {topic}\n{syn.read_text(encoding='utf-8').strip()}")
    for raw in sorted(raw_dir.glob("*-raw.md")):
        for m in re.finditer(r"URL:\s*(https?://\S+)", raw.read_text(encoding="utf-8")):
            urls.add(m.group(1).rstrip(").,"))
    return "\n\n".join(bullets), sorted(urls)


def _score_axis(axis: str, digest: str, urls: list[str]) -> dict | None:
    body = f"{_RUBRICS[axis]}\n\nDIGEST BULLETS:\n{digest}"
    if axis == "faithfulness":
        body += "\n\nREAL EVIDENCE URLS (the only valid citations):\n" + "\n".join(urls)
    return _extract_json(_run_claude(body))


def judge_run(date: str) -> dict | None:
    """Run the 3-judge panel over a date's digest. Returns the quality record or None."""
    digest, urls = _gather(date)
    if not digest.strip():
        return None
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = dict(zip(_RUBRICS, ex.map(lambda a: _score_axis(a, digest, urls), _RUBRICS)))

    quality: dict = {}
    issues: dict = {}
    for axis in _RUBRICS:
        out = results.get(axis) or {}
        sc = out.get("score")
        quality[axis] = int(sc) if isinstance(sc, (int, float)) else None
        if out.get("issues"):
            issues[axis] = out["issues"][:5]
    present = {a: quality[a] for a in WEIGHTS if quality.get(a) is not None}
    if present:
        wsum = sum(WEIGHTS[a] for a in present)
        quality["composite"] = round(sum(present[a] * WEIGHTS[a] for a in present) / wsum)
    else:
        quality["composite"] = None
    quality["issues"] = issues
    return quality
