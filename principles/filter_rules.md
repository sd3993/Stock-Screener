# Filter rules: triage and the gate

Standards for the two filters before the deep analysis: triage (a script) and the gate (a judgement). Both apply `/principles/investing_rules.md`; this file holds only what the filters add.

## Both filters
- **Holdings are never filtered:** they skip triage's rejects and the gate.
- **No sector filter:** `/principles/sector_rules.md` (market-wide screening).

## Triage (decided by `triage.py`; its `--help` has the exact rules)
- **Return math** at three projection lengths (2, 5 and 7 years; a stock's own visible-until date is only set in the analysis): the EPS growth needed for the CAGR hurdle at exit P/E = min(own 5-year median P/E, 30) (a script cannot judge re-rating evidence, so triage allows the re-rating; the gate and the analysis apply the rule), with dividends, against the growth visible in the trailing figures (conservative and optimistic).
- **Earnings evidence** (the earnings evidence rule): E1 acceleration, E2 re-rating candidate (a quality business at a P/E below its own range with growth intact), E3 sustained growth, E4 turnaround.
- **Queued for the gate:** a screen hit, or a non-screen name (the sweep) with earnings evidence, live return math and no hard flag; or an emerging company or participant (`/principles/sector_rules.md`) with no hard flag.
- **Rejected at triage only when clearly failed**, by a margin a data error is unlikely to flip: return math dead at every projection length even at the optimistic growth plus 5 points; promoter pledge above 25% of promoter holding; cash conversion below 0.3 over both 2 and 5 years; REITs, InvITs and investment companies. Anything near a line goes to the gate instead.

## The gate
- **A filter, not the analysis:** it removes only companies that clearly can't meet the rules; borderline ones go on to the analysis.
- **Guidance:** guidance from another company's document or older than 12 months counts as absent.
- **Return math** at the three projection lengths, at base-case EPS growth g: multiple ≈ (1+g)^years × exit P/E ÷ P/E now + years × dividend yield, years = 2, 5 and 7. g = management's numeric guidance where given (profit growth implied by revenue and margin guidance), haircut where its record of delivery is poor, else the sustained 3-year record tempered by the latest two quarters; never the latest quarter's spike. Where the sector entry gives a dated tailwind that the company's own filings show it is capturing (orders, capacity), say so; it can support g only through the company's own figures and guidance, never by itself. Exit P/E, its logged exceptions and one-off normalisation: the valuation and return math rule; say which exception was used and, where the exit P/E is above the P/E now, the forward evidence for the re-rating.
- **NEXT** when the best projection length's base-case CAGR (multiple^(1/years) − 1) is about 22% or more (rougher than the hurdle, so borderline cases reach S11) and no floor fails. Otherwise REJECT.
- **Emerging companies** (`/principles/sector_rules.md`): g may rest on the filed evidence of the new business (orders, approvals, dated capacity) where the trailing figures don't show it yet. With no numeric basis for g, the name goes NEXT when no floor fails, and the analysis decides. A **participant's** g rests on its established business, plus the emerging part only as far as filed evidence backs it.
- **Floors** (any one fails → REJECT): cash conversion below the non-negotiables' floor (CFO negative in both latest half-years fails); net debt/equity above the cash and debt rule's line (lenders: that rule's lender note instead); pledge per the pledge rule; promoter selling that fails the promoter selling and buying rule's tests; integrity flags (the integrity flags rule); holding/investment companies; a one-quarter profit spike off a tiny base with no guidance.
- **Re-gating:** a company already gated this quarter isn't re-gated unless it filed something new or its price has fallen 20% or more since its gate check.
