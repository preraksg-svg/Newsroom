# Zapway Newsroom — Test Plan

Framework: **pytest** (+ `pytest-asyncio`, both already in `requirements.txt`).
Scope: deterministic **core business logic** — no network, no live Groq/Playwright/DB.
Anything that needs the LLM, the browser, or the network is exercised only on its
**offline/guard path** (missing creds, blacklist heuristics) so the suite is fast
and hermetic.

## System architecture (as tested)

```
ingestion_worker ──► raw signals ──► ai_worker / system_orchestrator
                                          │
        relevance gates (backend.llm)     │  is_ev_focused, is_two_wheeler_story,
        quality gate  (content_scoring)   │  filter_article heuristics
        rewrite       (layer3 + llm)      │  clean_headline_garbage
        SEO meta      (seo_engine)        │  generate_seo_metadata (LLM) / text utils
        normalize     (text_format)       ▼  strip_inline_markdown
                                     create_draft (DB)
                                          │
        publish (zapway_publisher) ──► extract_bullets_from_content,
                                       flatten_markdown_tables
                                          │
        auto-share (x_publisher) ────► build_caption, post_to_x (guarded)
```

## Modules & cases

### 1. text_format.strip_inline_markdown  (`test_text_format.py`)
- Happy: `**bold**`, `*italic*`, `` `code` ``, `__x__` removed.
- Preserve: bullet markers (`* `, `- `), inline images `![](...)`, table pipes, `snake_case`, math `3*4`.
- Headings: `### H` → `H`. Links: `[t](u)` → `t`.
- Boundary/error: `None`, `""`, whitespace-only.
- **Idempotency**: `f(f(x)) == f(x)` (guarantees safe re-application across layers).
- Perf/ReDoS: pathological `*`×5000 returns quickly.

### 2. backend.llm.clean_headline_garbage  (`test_headline_clean.py`)
- Strip `" - Autocar India"`, `" | CleanTechnica"`.
- **Regression**: `"...company- Moneycontrol.com"` (no space before dash) → stripped.
- Must NOT strip hyphenated words: `e-scooter`, `well-known`.
- Error: `None`/`""`.

### 3. backend.llm relevance gates  (`test_relevance.py`)
- `is_ev_focused`: EV in headline → True; single passing mention in body → False; ≥3 body signals → True.
- `is_two_wheeler_story`: scooter/e-bike dominant → True; car+charging+policy context → False.
- `filter_article` OFFLINE heuristics only: blacklist term (`smartphone`, `ipl points`) → relevant False; no EV term → relevant False. (LLM path not invoked in these cases.)

### 4. content_scoring  (`test_scoring.py`)
- `compute_content_score` return shape: `content_score` (0–100), `decision` ∈ {APPROVE, IMPROVE, REJECT}, `sub_scores`.
- Rich, specific, multi-section article scores **higher** than a thin vague one.
- Thin/vague content → REJECT; strong content → not REJECT.
- Sub-scorers clamp to their ranges.

### 5. zapway_publisher formatting  (`test_publisher_format.py`)
- `flatten_markdown_tables`: `| a | b |` rows → `* ...` bullet lines; non-table text untouched.
- `extract_bullets_from_content`: `* x`/`- x` → bullets (emphasis stripped); ordinary lines → body; a `*`-prefixed line >200 chars stays in body (paragraph guard); returns `(cleaned_content, bullet_list)`.

### 6. x_publisher  (`test_x_publisher.py`)
- `build_caption`: ≤280 chars, includes hashtags, truncates long titles with `…`.
- `post_to_x` / `verify_x_connection` with NO creds → `skipped`/`connected False`, never raises, never touches network.

### 7. seo_engine text utils  (`test_seo_utils.py`)
- `truncate_word_safe`: never exceeds max, breaks on word boundary.
- `clean_incomplete_ending`: trims dangling trailing fragment.

## Out of scope (needs live services / covered by live probe)
- Real Groq generation, Playwright publish, Resend email delivery, DB persistence,
  X actual posting. These are validated via `/api/test-*` endpoints against the
  deployed service, not in unit tests.
