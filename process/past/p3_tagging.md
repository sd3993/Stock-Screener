# P3.0: business-type tagging brief (one helper per batch <N>)

Read first: `CLAUDE.md` (project rules), `process/past/p2_sample.md` (the "Business type" paragraph is the task definition: type list, columns, peers handling, shell flags), `process/future/f5_sector_map.md` step 1 (classify by what the business actually does), and `business_types/new_types.md` plus any `business_types/new_types_batch*.md` (types added by earlier batches: reuse them with the same names, no near-duplicates). Look at a few rows of earlier `batch_*.csv` files to match their style and detail.

Input: `business_types/batch_<N>_input.csv` (sym, as_of = window start date, groups); some companies have several window starts.

For each company read `data/companies/<SYM>/scr/overview.json`: the about text and `sectors` (screener's industry label, NSE's classification). The label is a coarse hint only: it is today's classification (wrong after a demerger or change of business) and catch-all bins say little, so the about text or the window-start report decides. Don't read `scr/peers.json`. The `peers` column now records whether the industry label helped/misled/neutral. Only when the about text leaves the type unclear, the company has several segments, or the business may have changed since as_of, read the segment split / business description in an annual report or presentation near as_of, from the exchange links in `scr/documents.json`: `curl.exe -s -m 60 -o <file> <url>` exactly (never add a browser user-agent or other spoofed headers) into the session scratchpad folder `ar<N>\` (never into the project). Some NSE links download a zip holding the PDF (unzip it); if a PDF's text is unreadable (scanned), use the neighbouring year's report. Type each row as of its as_of date: if the mix changed, the earlier window gets the earlier type. When no report before as_of is listed, say in evidence that the earlier mix is inferred from a later report.

Write `business_types/batch_<N>.csv`, one row per input row, columns:
sym, as_of, business_type, sub_type, revenue_drivers, cyclicality (low/medium/high), capital_intensity (low/medium/high), pricing_power (low/medium/high), customers (B2C/B2B/government, may combine with "/"), evidence (short: source, key facts), peers (helped/misled/neutral), flag (blank, or "shell" / "no real operations" / "unclear" with a reason).
Add a type only when a company truly doesn't fit; never edit new_types.md: write a new type (name, one-line definition) to `business_types/new_types_batch<N>.md`.

Rules: no scripts beyond reading files and downloads; edit no project file other than those two; don't fetch from screener; don't invent facts or use general knowledge, only the files and reports (thin evidence: say so and flag "unclear").

Return under 150 words: rows written, type counts, peers helped/misled/neutral (which companies misled), flags, new types, documents used and whether links worked.
