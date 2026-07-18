# Zapway Newsroom Project-Scoped Rules

## 1. Strict Geographic Focus
- **Rule**: The EV newsroom must strictly focus on **India-based EV news, launches, and infrastructure**. 
- **Action**: All global/non-Indian news signals must be automatically rejected at the scraping/ingestion layer and filtered out at the LLM level.

## 2. Minimal Rewriting Policy
- **Rule**: When rewriting or processing news signals, the AI engine must stay extremely close to the original source content.
- **Action**: Do NOT rewrite articles from scratch or expand them to arbitrary lengths (like 600-900 words). The AI should keep the original headline almost completely intact and modify only a few words in the body text for grammatical correction and natural SEO optimization.

## 3. Draft Retention & Timezone Accuracy
- **Rule**: The drafts column must accurately display all news from the last 48 hours.
- **Action**:
  - Always fetch news items with a high limit (e.g., `limit=1000`) to prevent drafts from being cut off by pagination.
  - Parse date strings with the `Z` suffix to force UTC date parsing. This prevents local timezone offset shifts from hiding active drafts early.

## 4. Complete Sentences Only & No Ellipses
- **Rule**: The system must never output incomplete sentences or truncate any generated news content, headings, meta titles, or meta descriptions with trailing dots/ellipses (`...`).
- **Action**: All truncation functions must only split at complete sentence boundaries (like periods, exclamation marks, or question marks) and must never append `...`.

## 5. Strip Metadata Headings
- **Rule**: The system must never ingest or generate publication dates, authors, or publisher signatures as news article headings.
- **Action**: All web scrapers and LLM engines must explicitly filter out layout metadata (e.g., dates, author signatures, brand titles) to prevent them from becoming rewritten article sections.
