# last30days Dashboard (Claude) — self-contained keyless research loop

A daily research loop that pulls what people are actually saying about your topics, synthesizes a
dark-mode digest, grades it with a cheap 3-judge quality panel, and tracks executive KPIs over time.

**Self-contained.** The research engine is **vendored in-repo** under [`engine/`](engine/) — a pruned,
**keyless-only** fork of [`mvanhorn/last30days-skill`](https://github.com/mvanhorn/last30days-skill)
(MIT). No external clone, no cookie/credential code (see [`engine/VENDORED.md`](engine/VENDORED.md)).

## Security model (keyless, no cookies)

- **Only 5 keyless sources:** Reddit, Hacker News, Polymarket, GitHub, YouTube. Nothing requiring an API
  key or browser cookies.
- The vendored engine has **all cookie-harvesting / X / TikTok / Instagram / session-auth modules
  deleted** — not just disabled. Triple-enforced at the orchestrator too: a `KEYLESS_SOURCES` allowlist,
  a **scrubbed subprocess env** (`engine_env()` strips every key/cookie var), and `EXCLUDE_SOURCES`.

## Layout

```
engine/        vendored keyless engine (last30days.py + lib/) · MIT · VENDORED.md
src/
  orchestrator.py   run / validate / doctor / kpi / rerender / judge
  render_digest.py  dark-mode digest (relevance sort, colored verdicts, per-bullet points)
  metrics.py        KPI store + dashboard (CFD, trends, breakdowns, watch list, quality)
  judge.py          3 cheap Haiku judges (Relevance / Faithfulness / Actionability)
  trending.py       Top-10 trending AI GitHub repos this week (keyless)
  duediligence.py   tool due-diligence: skill/MCP/integration brief per tool (dd command)
config/topics.yaml  research streams + topics
config/tools.yaml   tool due-diligence targets (plug-and-play: add a name, run `dd`)
skills/tool-dd/     portable SKILL.md wrapper (WebSearch-grounded due-diligence)
digests/  briefs/  raw/  metrics/  (generated; gitignored except metrics/kpi.jsonl)
```

## Prerequisites

| Tool | Notes |
| --- | --- |
| Python 3.12+ | Engine is pure stdlib. `run.cmd` resolves it user-agnostically (see below). |
| `gh` CLI (authed) | gates the GitHub source; the loop injects its dir onto the engine PATH. |
| `yt-dlp` | keyless YouTube source (binary on PATH; the loop adds the Python Scripts dir). |
| `claude` CLI | headless query-planning, synthesis, and the Haiku judges. |

Run `.\run doctor` to confirm all four resolve.

### Running in a fresh environment

The launchers are **user-agnostic** — there are no hardcoded usernames. `run.cmd` resolves Python
in this order: the current user's per-user install
(`%LOCALAPPDATA%\Programs\Python\Python313\python.exe`) → `py -3.13` → `py -3.12` → bare `python`.
`scripts\run-daily.ps1` derives the same from `$env:LOCALAPPDATA`. To set up a new machine:

1. **Python 3.13** — install it; the `py` launcher (bundled with the Windows installer) is the
   reliable fallback. The engine *rejects* anything below 3.12 (e.g. a default Anaconda 3.10).
2. **`gh auth login`** — authenticates the GitHub source (otherwise it's silently skipped).
3. **`yt-dlp`** on PATH (e.g. `pip install yt-dlp`) — gates the YouTube source.
4. **`claude` CLI** on PATH — required for synthesis and the judges.

No `.env` or API keys: every source is keyless, and `gh` / `claude` carry their own auth.

## Commands

Use the **`run` wrapper** at the repo root — it resolves Python 3.13 (your bare `python` is Anaconda
3.10, which the engine rejects) and forwards args. From the repo root in PowerShell, prefix with `.\`:

```powershell
.\run doctor                 # prereqs + active keyless sources
.\run validate               # RAW engine output for QE judgment
.\run run                    # research -> digest -> KPIs -> judge -> dashboard
.\run run --no-judge         # skip the quality scorer
.\run judge --date 2026-06-20 # re-score a day's digest only
.\run kpi --backfill         # rebuild dashboard (seed from existing digests)
.\run rerender               # re-emit digests after a style change
.\run dd "Azure App Insights" # tool due-diligence -> briefs/<slug>-<date>.html
.\run dd --all               # due-diligence every tool in config/tools.yaml
.\run dd "<tool>" --engine-only # raw keyless evidence (hook for the tool-dd skill)
```

**Tool due-diligence** (`dd`): given a tool name, research whether a drop-in
skill / MCP server / SDK exists, how to wire it, the gotchas + environment
prereqs, how mature it is, and what the community says — as a shareable 4-section
HTML brief. The baked-in command is keyless + autonomous; the portable
[`skills/tool-dd`](skills/tool-dd/SKILL.md) wrapper adds WebSearch-grounded
discovery for a materially richer Integration map.

> For unattended/scheduled runs use `pwsh -File scripts\run-daily.ps1 run` (resolves Python + gh, logs).

Each `run` writes `digests/YYYY-MM-DD.html`, appends a row to `metrics/kpi.jsonl`, and rebuilds
`metrics/dashboard.html`.

## The digest

Topics sorted **most-relevant-first** (by total engagement). Each bullet: *what changed / why it matters
/ verdict*, with the **verdict color-coded** (green Act · red Ignore · amber Watch) and the cited item's
**backing points** shown inline.

## The 3-judge quality scorer

After each run, three cheap **Haiku** judges score the whole digest (3 calls total):
- **Relevance** — on-topic and substantive vs. noise?
- **Faithfulness** — do cited links match the run's real evidence URLs (no fabricated citations)? *(the
  QE trust gate)*
- **Actionability** — are the verdicts sound and the takeaways useful?

Composite (faithfulness-weighted) lands on the dashboard as a **Digest quality** card + trend, and a
**red banner** fires if faithfulness drops below 70 (possible unsupported citations).

## Dashboard KPIs

Top to bottom:
- **Top-10 trending AI repos this week** — keyless scrape of `github.com/trending?since=weekly`
  (AI-filtered, star-velocity), refreshed on every dashboard rebuild.
- **Cumulative Flow Diagram** — cumulative interactions per **stream** as stacked bands over the last
  ~14 runs (2-week trend).
- **Interactions per run** (source-outage runs flagged ⚠), **stream trend**, and per-topic / per-stream
  **breakdowns** for the latest run.
- A sticky **Read / Watch list** (Act + Watch items, clickable) on the right.
- KPI cards: cumulative + latest interactions, **digest quality**, **source health** (an outage shows as
  ⚠, never a mysterious cliff), citations, YouTube reach.

Interactions = upvotes + points + reactions + comments (YouTube views tracked separately as reach).

## Scheduling

`scripts\run-daily.ps1` resolves Python + `gh` and runs the loop; register it with Windows Task
Scheduler for a daily cadence (see the script header).
