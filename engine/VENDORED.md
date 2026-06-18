# Vendored engine — provenance & modifications

This `engine/` is a **pruned, keyless-only fork** of the `last30days` research engine,
vendored so this repo has no dependency on an external clone.

## Source

- **Upstream:** https://github.com/mvanhorn/last30days-skill
- **License:** MIT (see `LICENSE`) — author **mvanhorn**. MIT permits this fork; attribution retained.
- **Vendored from commit:** `2cc88ecaf1f2445eae0276709cd60d9166e32c8d`
- **Vendored on:** 2026-06-18
- **Original path:** `skills/last30days/scripts/` → here as `engine/`

## What was removed (and why)

This fork keeps **only the 5 keyless sources** (Reddit, Hacker News, Polymarket, GitHub, YouTube)
and the shared core. Everything requiring cookies, browser sessions, paid keys, or session auth was
**deleted** — both to shrink the trust surface and because the orchestrator never uses them.

**Deleted modules (`lib/`):**
- Browser-cookie harvesting: `chrome_cookies`, `safari_cookies`, `cookie_extract`, `setup_wizard`
- X / Twitter: `bird_x`, `xurl_x`, `xai_x`, `xquik`
- Paid / session-auth social: `tiktok`, `instagram`, `threads`, `bluesky`, `truthsocial`, `pinterest`,
  `digg`, `xiaohongshu_api`, `perplexity`
- Job-board source: `hiring_signals`, `jobs`
- Unused top-level scripts: `briefing.py`, `evaluate_search_quality.py`, `test_device_auth.py`,
  `verify_v3.py`, `watchlist.py`

**Edited to de-reference the deletions:**
- `lib/pipeline.py` — trimmed the top-level `from . import (...)` block to keyless + core only.
- `lib/env.py` — `get_x_source`, `get_x_source_with_method`, and `get_x_source_status` now return
  "no X source" (they previously imported `bird_x` / `xurl_x` unconditionally). The lazy
  `cookie_extract` import in `extract_browser_credentials` is already `try/except ImportError → {}`.

## Local patch carried over the upstream

- `lib/hackernews.py` — the `points>2` term was removed from the Algolia `numericFilters` (Algolia
  dropped `points` from `numericAttributesForFiltering` ~2026-06-17, causing HTTP 400 → "0 items");
  the `points > 2` quality bar is now applied client-side after fetch. **This bug is unfixed upstream**
  as of the vendored commit — re-check before pulling any upstream update into this fork.

## Known cosmetic leftovers (harmless, unreachable)

`pipeline.py`'s per-source fetch dispatch still contains branches for the removed sources (e.g.
`tiktok.search_and_enrich(...)`). These are **dead code** — unreachable because `available_sources()`
never lists a removed source under a scrubbed/keyless environment, and the orchestrator's
`KEYLESS_SOURCES` allowlist + scrubbed `engine_env()` triple-guard it. Verified: `--diagnose` and a
live keyless fetch both run clean. A future pass can delete these branches for tidiness.

## Dependencies

Pure Python **stdlib** — no `pip` packages required. YouTube uses the external `yt-dlp` binary
(installed separately, on PATH). Requires **Python 3.12+**.
