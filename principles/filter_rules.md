# Filter rules: triage and the gate

Standards for the two filters before the deep analysis: triage (a script) and the gate (a deep-tier judgement). Both apply `/principles/investing_rules.md`; this file holds only what the filters add. How each runs: `/workflow/WORKFLOW.md`.

## Both filters
- **Holdings are never filtered:** holdings skip S3's rejects and S8's gate and always go on to S9, so they run through the full analysis (full mode) or the marker check (recheck mode) with fresh figures.
- **No sector filter:** a company is never rejected for being outside a tailwind sector; a company in a low-growth industry is queued like any other.

## Triage (decided by `triage.py`; its `--help` has the exact rules)
- **Return math** per horizon (short 2 years, medium 5, long 7): the EPS growth needed for the CAGR hurdle at exit P/E = min(own 5-year median P/E, 30), with dividends, against the growth visible in the trailing figures (conservative and optimistic).
- **Earnings evidence** (the earnings evidence rule): E1 acceleration, E2 stalwart rebound, E3 sustained growth, E4 turnaround.
- **Queued for the gate:** a screen hit, or a non-screen name (the sweep) with earnings evidence, live return math and no hard flag.
- **Rejected at triage only when clearly failed**, by a margin a data error is unlikely to flip: return math dead in every horizon even at the optimistic growth plus 5 points; promoter pledge above 25% of promoter holding; cash conversion below 0.3 over both 2 and 5 years; REITs, InvITs and investment companies. Anything near a line goes to the gate instead.

## The gate
- **A filter, not the analysis:** it removes companies that clearly can't meet the rules, and keeps borderline ones for the full analysis (S13).
- **Guidance:** guidance from another company's document or older than 12 months counts as absent.
- **Return math** per horizon at base-case EPS growth g: multiple ≈ (1+g)^years × exit P/E ÷ P/E now + years × dividend yield, years = 2 (short), 5 (medium), 7 (long). g = management's numeric guidance where given (profit growth implied by revenue and margin guidance), haircut where its record of delivery is poor, else the sustained 3-year record tempered by the latest two quarters; never the latest quarter's spike. Where the sector entry gives a dated tailwind that the company's own filings show it is capturing (orders, capacity), say so; it can support g only through the company's own figures and guidance, never by itself. Exit P/E: the own 5-year median P/E capped at 30, judged lower when that history is inflated by depressed past earnings, too short (listed under ~2 years) or the business is cyclical at a peak (use mid-cycle); say so. Normalise one-offs before any P/E.
- **NEXT** when the best horizon's base-case CAGR (multiple^(1/years) − 1) is about 22% or more (rougher than the hurdle, so borderline cases reach S13) and no floor fails. Otherwise REJECT.
- **Floors** (any one fails → REJECT): cash conversion below the non-negotiables' floor (CFO negative in both latest half-years fails); net debt/equity above 0.8 (lenders: the cash and debt rule's lender note instead); pledge per the pledge rule; promoter selling that fails the promoter selling and buying rule's tests; integrity flags (the integrity flags rule); holding/investment companies; a one-quarter profit spike off a tiny base with no guidance.
- **Re-gating:** a company already gated this quarter isn't re-gated unless it filed something new or its price has fallen 20% or more since its gate check.
