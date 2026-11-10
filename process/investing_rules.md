# Investment rules (the only copy)

The only copy of the investing rules; other files point here. Who may change what in it: `COMMON_AI.md` ("Rules file").

- **General rules** are Shouvik's; several act as gates. **Sector notes** sit as sub-points under the general rule they adjust, and exist only for sectors already researched in depth (list at the end); a company in a sector with no notes is analysed on the general rules and flagged.
- **Tags** say where each point came from: **[Yours]** Shouvik's rule; **[Expert: name, work]** a named, proven practitioner; **[Learned: SYM, document]** found in a company's filings during research. Opinion pieces and anonymous websites are never sources.

## Buckets (horizons) and the hurdle [Yours, 23 Oct 2026]
| Bucket | Horizon | Return math projected to | Exit P/E role |
|---|---|---|---|
| Short term | ~1-2 years | year 2 | the target: sell at it (sell trigger) |
| Medium term | ~3-5 years | year 5 | where the P/E is expected to settle; not a sell trigger |
| Long term | 5+ years | year 7 | same as medium; usually at or below the medium-term exit P/E as growth slows |

- No fixed return target per bucket. A stock is eligible for a bucket when the evidence for that horizon holds (rule 7). Eligibility is nested: a long-term stock is also in medium and short, and a medium-term stock is also in short (near-term visibility can't be missing when longer-term visibility exists); its CAGR in the shorter buckets may be lower, and flagged red.
- **Holdings are always listed** (Shouvik, 23 Oct 2026): every stock held, even a full exit, appears in the bucket(s) it belongs to, or, if eligible for none, in the closest one; every reason (non-negotiable fail, not eligible, below hurdle) shows in red, so a temporary or marginal miss can be judged before selling.
- **Hurdle (all buckets):** base-case expected return of at least **25% a year (CAGR)** to the bucket's horizon end, and the bear case no worse than ~0.8x. A stock that falls below the hurdle or any other price-based rule (forward P/E, PEG) stays listed, flagged in red with every reason shown, so short-lived price moves don't make it vanish; buy/sell decisions weigh the flag. Only a new deep analysis (S13: eligibility, non-negotiables) can remove it from a bucket.
- **Ranking:** within each bucket, by base-case expected CAGR (highest return in the least time), with evidence quality shown alongside. How long a stock is held is decided by later quarterly runs (upgraded, downgraded or dropped from buckets), not fixed upfront.
- "100x" is a tag inside the medium- and long-term buckets.

---

## 1. Non-negotiables (all buckets; gates)
Judged on today's level AND the direction over the last 2-3 quarters (other factors use 1-2 quarters). One can pass while still below its line only if it is not too low today, has improved for 2+ consecutive quarters, and the cause is found and logged. [Yours, revised 20 Oct 2026] Permanent loss comes from fraud, leverage and forced selling. [Expert: Howard Marks, *The Most Important Thing*]

1. **Pledge** (incl. pledges of the promoter's holding company): passes at 0; or at ≤10% of promoter holding while being released over the last 2-3 quarters with no new pledge. Fails above ~20%, or on any new pledge in the last 3 quarters. [Yours]
2. **Promoter selling and buying** (promoter group as a whole) [Yours, revised 3 Nov 2026]: a sale is never a fail by itself; a promoter with a large stake is expected to sell some so institutions and the public can build positions. Look for the reason (exchange filings, call transcripts, AGM proceedings, filed press releases) and log it with the sale's size, but judge on these tests:
   - **Selling fails** when the promoter group ends below 50% after the sales, or when results worsen for 2-3 consecutive quarters during or around the sales (a one-off dip doesn't count). "Results" means profit and operating cash flow together: profit growth with weak cash conversion around the sales counts as worsening.
   - **Selling also fails** when it comes shortly before an adverse event the company later discloses (a lost order or customer, regulatory action, a downgrade), or when it funds a stressed group company (seen as group pledges or group debt).
   - **Selling passes** otherwise, including sales followed by good results.
   - **Buying passes** at a promoter-group holding of 40% or more, whatever the recent results, when it is real cash buying (open market, or a preferential issue or warrants paid in cash, not ESOPs) and there is no pledge; any weakness is left to the full analysis (S13).
   - A co-promoter family's or PE promoter's exit is judged on the same tests and logged.
   - All sectors: weigh a small promoter-group sale against promoter buying or preferential subscription in the prior 12 months (the net flow), not on its own. [Learned: SEJALLTD, allotment 17 Dec 2025 vs sale 16 Sep 2026]
   - All sectors: sales by promoter-group family members count, even when the CMD is buying; check the promoter-group pages of the SHP each quarter. [Learned: MOLDTECH, BSE SHP Jun/Sep 2026]
   - All sectors: check the parent promoter's own pledge, debt and credit rating; a highly pledged or downgraded parent fails the child (INDOTECH rejected over parent SSEL's 82.41% pledge and an [ICRA]BB+ downgrade). [Yours, Oct 2026]
   - Foreign-parent promoters (e.g. a rating agency owned by a global parent): judged on the parent's stated intent and stake trend, not the 40% line alone. [Learned: ICRA dossier]
3. **Governance:** integrity flags are absolute (auditor resigning over concerns, money moved to related parties, forensic audit, SEBI/ED/fraud orders). Softer items (related-party deals, a resolved regulatory notice, board changes) are judged on trend. [Yours] Related-party transactions and auditor changes are the first forensic checks. [Expert: Saurabh Mukherjea, *Coffee Can Investing* (forensic accounting chapter)]
   - All sectors: an auditor resignation, or a third preferential issue inside ~14 months, is checked before any return math. [Learned: 513472 Simplex Castings, BSE filings Aug 2026]
4. **Cash conversion** (operating cash flow / profit): passes at ≥0.65 over 3-5 years; or at ≥0.4 over 3 years when each of the last two half-years is better (cash flow is published only half-yearly, so quarterly debtor/inventory days and collections support the trend). Fails below 0.4 even if improving. [Yours] Cash flow, not reported profit, is the test of earnings quality. [Expert: Mukherjea, *Coffee Can Investing*; Buffett, owner earnings, Berkshire letter 1986]
   - **Capital goods / EPC / process equipment:** milestone billing makes Q4 dispatches land as March receivables; judge over 3 years and the H1/H2 pattern, never one year. A promise of "realisation next quarter" is checked against the next half-year cash flow. [Learned: KLBRENG-B, Q4 FY26 and Q1 FY27 calls; JASH]
   - **Defence electronics:** long development cycles and PSU customers make CFO/PAT structurally low (0.18 over 5 years at one company). Treat as structural unless the cash conversion cycle has fallen for 2+ half-years. [Learned: DATAPATTNS, BSE XBRL FY24-26]
   - **Metal recycling / import-scrap models:** heavy hedged and in-transit inventory gives weak H1 and strong H2 every year; judge on full years and 3-year totals. [Learned: GRAVITA, AR FY26 cash flow]
   - **Packaging / polymer converters:** stocking raw material ahead of polymer price rises and new-capacity WIP depress CFO; check whether the inventory days return after the price move. [Learned: KNACK, CARE Apr 2026 rating note]
   - **Companies with large treasury books (e.g. rating agencies, cash-rich software):** interest and fair-value gains sit in profit but in investing cash flow (Ind AS 7), so CFO/PAT reads low. Compute CFO / (PAT − post-tax other income) as well; pass on that figure when the gap is fully explained by treasury income. [Learned: ICRA, AR cash-flow statements FY22-26]

## 2. Trajectory, plans and root cause (every rule)
Judge each metric on three things together: the trailing value, its direction (last 1-2 quarters for ordinary factors; 2-3 quarters for non-negotiables), and any plan already in execution with a milestone within 1-2 quarters (capacity commissioning, price increases, working-capital release, order execution, debt repayment). For every negative, log: (a) the cause, with its source; (b) temporary or structural; (c) how management handled the same problem before (past cycles, delivered vs missed guidance); (d) whether it is improving now. A weak trailing number with a found, temporary cause and an improving trend is not a rejection; a good trailing number with a deteriorating latest quarter is a warning. Outside the integrity flags, weigh what a stock passes against what it fails. [Yours, 20 Oct 2026] Know why the numbers moved. [Expert: Peter Lynch, *One Up on Wall Street*] Cheap stocks with improving fundamentals beat cheap stocks without. [Expert: Joseph Piotroski, "Value Investing" (2000)] Earnings acceleration. [Expert: William O'Neil, *How to Make Money in Stocks*]
- **Likelihood of scenarios** [Yours, 3 Nov 2026]: the base case follows the most likely path; if it needs several uncertain things to all go right, mark evidence quality low and use the likelier path. The bear case is a realistic setback (one or two things going wrong), not everything bad at once. Any case, good or bad, that needs many independent things to coincide is taken with a grain of salt, not as fact. A thesis that breaks is rewritten if the stock is still favourable on the new one; only a case that turns unfavourable (below the hurdle or not eligible) changes the verdict.
- **Turnaround checks** [Yours, Oct 2026]: 2-3 quarters of sequential (QoQ) improvement, not YoY base effects; cause classified structural vs cyclical/one-off and confirmed by 2+ independent sources; operating cash flow follows profit within 2-4 quarters; promoter buying or holding at the low; stock still trough-priced; balance sheet can survive until the tailwind arrives; tailwind specific and dated; exit if the next 1-2 quarters reverse. Even when recent results are declining, check forward guidance, order book and upcoming strategic changes. Multibaggers are best bought at their low point with strong, dated tailwinds.
- **All sectors, guidance record:** keep a per-company guidance-vs-actual scorecard [Yours]; score delivered vs guided for the last 4-8 quarters before using guidance. A cut mid-year (e.g. 860 → 825 → delivered 736 cr) or a missed own floor means the next guidance gets a haircut in the base case. [Learned: JASH, KPEL, NEWGEN, TANLA calls FY26-27] Judge management's candour about bad news. [Expert: Philip Fisher, *Common Stocks and Uncommon Profits*, point 14]
- **Capital goods / EPC:** a quarter's collapse can come from deliberately delayed order intake; fixed-price contracts then lock the margin reset for the year, so the "temporary" call must say for how long. [Learned: ANUP, Q1 FY27 results and call 6 Aug 2026]
- **Programme-driven businesses (Kavach, single large government programmes):** when management itself says programme revenue may decline after a date, earnings are at a programme peak; base case must not extrapolate the peak. [Learned: HBLENGINE, FY26 AR; BSE note 24 May 2026]

## 3. Governance (other)
Promoter holding above 50% (40% if no pledge, and 40% for a promoter group that is buying, per rule 1.2), judged by trend: a fall of more than 5 points in 3 years passes only if it meets rule 1.2's tests (or is dilution, below). [Revised 3 Nov 2026] Main board preferred; SME allowed only with high conviction, sized so one lot keeps the stock near 10-12% and its sector within 20%. Long term: owner-operators preferred. [Yours; Expert: Christopher Mayer, *100 Baggers*]
- **All sectors:** a stake fall from equity issues or warrant conversions is dilution, not selling, but counts against "no repeated dilution" (rule 4). [Learned: KRISHNADEF, EFCIL shareholding filings]
- **EPC / group-captive businesses:** revenue concentrated in a sister company (71% at one EPC contractor) is a related-party exposure: discount the exit P/E and check pricing and receivables from the group. [Learned: KPEL, FY26 AR]

### Customers and markets [Yours, Oct 2026]
Avoid companies heavily reliant on a very small list of customers. Prefer high exports, especially to developed markets (US, EU, UK, UAE, Singapore and similar).

## 4. Cash and debt
Debt is fine when it funds capex backed by orders or contracts and the balance sheet can carry it: net debt/equity below 0.8, current ratio ≥1.25, interest coverage (EBIT / interest) ≥3x, net debt / EBITDA ≤2.5x. Debt that funds receivables or inventory (customers not paying) is a cash-conversion problem, not a capex one. No repeated equity dilution to fund growth. [Yours, 20 Oct 2026; Expert: Piotroski (falling leverage, rising current ratio, no new shares); Lynch]
- **All sectors, what counts as debt:** compute net debt both with and without lease liabilities (Ind AS 116) and report both; leases are debt-like obligations. [Expert: Aswath Damodaran, *Damodaran on Valuation* (operating leases as debt)] Vendor financing, usance letters of credit and acceptances for capex count as debt. [Learned: KPEL (vendor financing 215 cr), SANGHVIMOV (usance LC 336 cr), FY26 ARs] Margin money and earmarked issue proceeds are not free cash. [Learned: POWERMECH, DSSL]
- **Lenders (banks, NBFCs, brokers, insurers):** borrowing and deposits are the business, so the net debt/equity, current ratio and net debt/EBITDA tests don't apply. Judge capital adequacy, asset quality (gross and net NPA, credit cost) and leverage against the regulator's limits instead. [Learned: 31 lender filings in the FY27Q2 BSE balance-sheet re-harvest, 24 Oct 2026]
- **IT system integrators with leased equipment:** lease liabilities can grow fast (2.6 → 155 cr in two years) and must be in the debt tests. [Learned: DSSL, AR FY26]
- **Equipment rental (cranes):** fleet capex is debt-funded by design; track interest cover trend and management's own D/E ceilings. A ceiling raised every year ("not beyond 0.35" → 0.72 → 0.80) is guidance creep and a negative. [Learned: SANGHVIMOV, AR FY26 and calls]
- **Spread businesses with fast growth (speciality carbon, chemicals):** borrowings that jump with receivables and shrinking supplier credit inside a half-year are working-capital debt, not capex debt. [Learned: HSCL, Sep-26 balance sheet]

## 5. Government customers
Judged by outcomes: debtor days above ~120 or cash conversion below 0.65 fails. Government-dependent names capped at 20-25% of the portfolio. RBI, NPCI, Railways and defence buyers count as government; PSU customers often pay late. [Yours]
- **Defence electronics:** debtor days of 280-300 on government/PSU customers are normal for the model, so the 120-day line fails such names unless collections have improved for 2+ half-years. [Learned: DATAPATTNS, BSE XBRL]
- **Government IT projects:** go-live/milestone billing pushes debtor days up as order sizes grow; check >1-year receivables and ECL. Long OEM payables can offset (net cycle matters). [Learned: DSSL, AR FY26 note 8]
- **Healthcare paid by government schemes:** read the receivables ageing note: the share over 1 year and the ECL/write-offs, not just debtor days (which can fall while ageing worsens). [Learned: JSLL, AR FY26 note 12]
- **Water / Jal Jeevan Mission EPC:** state-scheme execution slowdowns hit both revenue and receivables. [Learned: IONEXCHANG, Q1 FY27 presentation]

## 6. Earnings evidence
- **Short term:** either (a) acceleration: latest quarter EPS +25% or more with sales +20% or more, rising over 2-3 quarters (O'Neil), or (b) stalwart rebound: a quality business (ROCE above 20%) at a P/E clearly below its own 5-year range with growth intact (Lynch buys stalwarts for 30-50%). Plus a dated catalyst within 2-4 quarters. Do not chase post-results spikes: Indian evidence for post-earnings drift is weak.
- **Medium term:** EPS growth strong enough to clear the hurdle at a justified exit P/E, or lower growth plus a justified re-rating from a low P/E, or a verified turnaround.
- **Long term:** sustained high EPS growth with ROCE above 20% and a long reinvestment runway. Rare: of 283 Indian firms growing 25%+ in 2003, only 103 kept it up for 5 years, so guidance gets a haircut.

[Yours; Expert: O'Neil (CAN SLIM); Lynch; Raamdeo Agrawal / MOSL Wealth Creation Studies (growth persistence)]
- **All sectors, one-offs:** strip deferred-tax reversals, MAT credits, tariff refunds, fire losses and exceptional items before growth or P/E. [Learned: POWERICA (deferred tax), VAIBHAVGBL (MAT credit 46.7 cr, IEEPA tariff refund), AR26 and Q1 FY27 notes]
- **Software products:** licence-deal timing makes single years lumpy; a shift from licences to subscriptions lowers near-term revenue without a business decline. Separate the two before calling a slowdown structural. [Learned: NEWGEN, Q3-Q4 FY26 calls]
- **CPaaS / messaging:** SMS pricing erosion is structural; growth must come from WhatsApp/RCS mix. [Learned: TANLA dossier]
- **Commodity-linked specialities (gelatin, masterbatches):** volume growth with falling realisations is not earnings growth; check realisation per unit. [Learned: NITTAGELA, AR FY26 MD&A; PLASTIBLEN]

## 7. Visibility (bucket eligibility, decided in S13)
- **Short term:** already contracted or in the numbers: executable orders at least equal to next year's revenue, capacity already running, price increases passed through.
- **Medium term:** order book 1.5-2.5x revenue, or funded capacity commissioning within 1-2 years.
- **Long term:** market at least 10x current revenue; growth that can last 10-15 years; funded plans for 3-4x capacity.

[Yours; Expert: Agrawal, QGLP (Longevity)]
- **Capital goods / EPC / defence:** count only firm orders filed with the exchange; L1 positions, LoIs and MoUs don't count (rule 16). Check the order book's executable period, not just its size. [Yours, rule 16; Learned: POWERMECH, HBLENGINE]
- **Export-heavy engineering:** order books can be stuck by tariffs or shipping disruption; tag export orders by destination risk. [Learned: JASH, Nov 2025 and Jun 2026 calls]

## 8. Valuation and return math
Measured on forward earnings: base and bear EPS paths to each eligible bucket's horizon end (years 2, 5, 7), built from guidance, order book and capacity coming online (step 2, price-independent). Expected multiple = horizon-end EPS × exit P/E (+ dividends) ÷ today's price; expected CAGR = multiple^(1/years) − 1 (computed live in the sheet from the step-2 figures). An exit P/E is set per eligible bucket. Starting point for the exit P/E = the stock's own 5-year P/E ("Historical PE 5Years" in Tapetide's screener, the 5-year median), capped at 30, so the multiple can re-rate up or down. Logged exceptions: recent listings use the median of listed peers; when the own figure was inflated by years of depressed or loss-making profit (turnarounds, post-IPO froth, boom years) a lower peer-based or judged exit P/E is used. Cyclicals (metals, commodity chemicals, capital goods, logistics, cranes) are valued on mid-cycle earnings, not trailing: at the bottom the P/E looks high because profit is depressed, at the peak it looks low. Profit is normalised for one-offs (tax credits, fire losses, write-offs) before the P/E is computed. For high-payout stocks, dividends received count toward the target. Every listing shows the share of the return that comes from re-rating, and a bear case; at an unchanged P/E most names give only ~1.5x in 3 years, so the re-rating needs a reason (growth recovering, P/E below peers and own history, buyback). PEG between 0 and 1 preferred; a negative PEG (falling or negative earnings) or a PEG above 2 is avoided.
- **Short and medium term:** a forward P/E of 50 or more at entry fails. [Expert: Agrawal/MOSL Wealth Creation Studies: 50x+ entries mostly destroyed wealth over the next 3 years] When the hurdle only works at a P/E above the stock's own average, set a buy-below price instead of buying now. [Yours]
- **Long term:** can pay more for longevity, but not 50x or more. [Expert: Agrawal/MOSL]

[Yours, revised 20 Oct 2026; Expert: Lynch (PEG; cyclicals on mid-cycle earnings); Benjamin Graham & David Dodd, *Security Analysis* (average earnings over a cycle); Agrawal/MOSL Wealth Creation Studies (reasonable price non-negotiable; PEG; re-rating on recovering RoE)]

**Exit P/E sanity checks (S13)** [Yours, 23 Oct 2026]:
- **Hand-picked peers:** name 3-6 genuinely comparable listed companies (from the annual report's competitor mentions and the business mix, not the data provider's sector label) and compare the exit P/E with their 5-year median P/Es and the stock's own history; explain any gap.
- **Growth at exit:** the exit P/E should be no more than about 2x the EPS growth rate (%) expected at the horizon's end (an exit PEG of ~2 at most); e.g. growth slowing to 12% supports an exit P/E of about 24 at most.
- Both sit under the cap of 30.

**Re-rating share** = ln(exit P/E ÷ today's P/E) ÷ ln(expected multiple): the part of the return that comes from the P/E change rather than earnings growth (negative when the P/E is expected to fall).
- **All sectors, SME-era histories:** a 5-year median that includes the NSE Emerge / BSE SME years is treated as inflated; the cap binds and a peer-based check is logged. [Learned: KRISHNADEF, JASH]
- **All sectors, boom-year re-ratings:** when 1-2 boom years lift the 5-year median well above the stock's longer history (e.g. 45-49x vs 18-23x), use a judged exit between the longer-run median and the cap. [Learned: NEWGEN, screener year-end P/Es FY19-26]
- **Capital goods / EPC / cranes:** check whether trailing earnings are at, below or above mid-cycle (industry down year, margin vs 5-year average) and say which; a turnaround off near-zero profit inflates the median, so an exit of ~25 is logged. [Learned: ACE, KIRLOSBROS, KLBRENG-B, MACPOWER]
- **Spread businesses near record EBITDA (coal-tar pitch, carbon black, gelatin):** 30 is a ceiling, not a target; test sensitivity at 25. [Learned: HSCL, NITTAGELA]
- **Programme-peak earnings:** value at below the cap (HBL used 25) when management flags the programme may decline. [Learned: HBLENGINE]
- **Group-captive revenue:** discount the exit P/E for revenue concentrated in a related company. [Learned: KPEL]
- **Market premium for optionality** (aerospace, semiconductors, LNG): a P/E far above the cap with growth under ~25% is a de-rating risk, not a reason to raise the exit P/E. [Learned: INOXINDIA, MACPOWER]

## 9. Size
- Short term: any size works (mostly mid caps, some large).
- Medium term: ideally under ~₹25k cr (mostly mid and small caps, rarely micro).
- Long term: ideally under ~₹5k cr (mostly small and micro caps, some mid). MOSL 2020-25: the fastest wealth creators started at ₹1.2k-15k cr, mostly at low entry P/Es.

[Yours; Expert: Mayer, *100 Baggers*; MOSL 30th Wealth Creation Study]

## 10. 100x tag (within the medium- and long-term buckets)
SQGLP: small Size, Quality, Growth, Longevity, reasonable Price. Kedia's SMILE: Small size, Medium experience, Large aspiration, Extra-large market potential. Clean, owner-operator management. Start at 2-3%; hold through volatility unless the thesis breaks. [Expert: MOSL 100x study (SQGLP); Vijay Kedia (SMILE); Mayer; Thomas Phelps, *100 to 1 in the Stock Market*]

## 11. Market and sponsorship
Short term: prefer a rising market and rising institutional holding. Medium term: a plus, not required. Long term: not required; early ideas are often under-owned. [Expert: O'Neil]

## 12. Exit rules
- Short term: sell at the target price (exit P/E × horizon-end EPS), or on the first quarter or event that breaks the thesis, unless a later run upgrades the stock to a longer bucket. Never add to a damaged thesis.
- Medium term: review each quarter; exit after 2 quarters of reversal. Sell fast growers when growth starts slowing.
- Long term: exit only if the thesis breaks.
- A stock in several buckets that hits its short-term target sells only its short-term share (its position split equally across its buckets); the rest stays.
- Trim/exit triggers: market cap above ~₹15-20k cr, P/E above 50, or two quarters of falling revenue and OPM; timed around the long-term capital gains date. Re-verify data each quarter. Buying back a stock sold earlier is fine if it qualifies for a bucket again. [Yours, Oct 2026]

[Yours; Expert: Lynch; Mayer]

## 13. Position size and count
10-15 stocks in total (roughly 4-5 per bucket). Short term: start ~4%; scale to 6-7% after the next quarter or a confirmed event. Medium and long term: ~5% to start (100x tags and micro caps 2-3%, as thin trading makes them harder to exit); add as the thesis is confirmed. [Yours (10-15 stocks); Expert: Agrawal (15-20 stocks, 10% single-stock cap at MOSL MF)]

## 14. Tax
Gains within 12 months are taxed at 20% (a 30% gain is about 24% after tax); long-term gains at 12.5%. The 12-month date is weighed before any sale. [Indian capital gains rules]

## 15. Bent-rule tier (taking risk with support)
A stock may bend up to 2-3 rules (never an integrity flag; non-negotiables only within the floors in rule 1) when the other principles give strong support: (a) asymmetric payoff: base case at or above the hurdle AND bear case no worse than ~0.8x over the bucket's horizon; (b) the bent metric has improved for 2-3 quarters and/or the Piotroski score is 6 or more; (c) valuation at or below its own history; (d) management has fixed similar problems before. Size: 2-3% starter; add only once the bent metric is back inside the rule. All bent-rule names together ≤30% of the portfolio. Each has a written kill condition and a review date. Breaching the stock or sector cap needs confirmed visibility (filings, contracts, notified policy). [Yours, 20 Oct 2026; Expert: Marks; Mohnish Pabrai, *The Dhandho Investor*; Piotroski; Kedia]

## 16. News and events
Counts only when confirmed in writing by the official source: exchange filings for companies; PIB, gazette, ministry or regulator for government. Firm orders and notified policies only, not MoUs, LoIs or L1 positions. Size the event against revenue; note when it reaches the P&L. Be sceptical of good news near promoter selling, a preferential issue or a QIP. Check whether the price already moved. Guidance and news come only from exchange disclosures (transcripts, presentations, results releases, AGM proceedings, annual reports, announcements), never from news sites. [Yours, Oct 2026; 23 Oct 2026]

## 17. Data verification
Filings are ground truth; data providers' figures (screener and any other) are checked against them. The full rule (sources, exchange choice, document ranking, mismatch handling) is in `process/data_rules.md`. [Yours, 20 Oct 2026; revised 23 Oct 2026]

## 18. Allocation and rebalancing [Yours, 23 Oct 2026]
- **Position size follows the stock's total potential and conviction,** not the number of buckets it is in. Potential going up or down is what drives buy, add, trim and sell.
- **Bucket ranges** (target 35% short / 35% medium / 30% long): short 25-40%, medium 30-45%, long 20-35%. A stock's position counts equally toward each bucket it is in (6% in two buckets = 3% each). A stock moving into or out of a bucket only shifts that split; it is not by itself a reason to trade. If a bucket has too few strong names, the money goes to the next best-ranked names, not to weak ones.
- Add when a stock falls with the market and its thesis is intact (short term: only if the catalyst is still inside the window). Trim or sell when a stock spikes on hype beyond its justified case. Sector cap ~20%; government-dependent names 20-25%; bent-rule names ≤30%. Don't leave much capital idle; unfilled weight sits in a liquid fund. Size positions by how well the thesis is verified.
- **Execution** [Yours]: Wave 1 and Wave 2 targets are a percentage of the final (Wave 2) position target. Front-load Wave 1 at 70% on confirmed low-YoY-base beats; execution-dependent low-base stocks 50%; high-YoY-base stocks expected to print negative headline YoY profit 0-20% Wave 1 / 80-100% Wave 2, to buy the post-results dip. Don't sell core holdings that already sit above their Wave 1 cap. No intraday trades (₹30 + GST brokerage, delivery STT/DP charges, FIFO resets the LTCG clock).

## 19. Buying after a fall
A falling price is not a negative on its own: when the business is intact and the fall has a found, temporary cause, the risk is lower, not higher. Buy in 2-3 tranches. Prefer names where the hurt metric has already turned for at least one quarter over catching a falling price (avoids value traps). For cyclicals, buy when earnings are depressed and the cycle indicators turn, not when the trailing P/E looks low. [Yours, 20 Oct 2026; Expert: Marks; Piotroski; Lynch; Rakesh Jhunjhunwala (crashes as the time to accumulate quality)]

## 20. Research process and rechecks
The process, rechecks and stopping rules are in `process/README.md` and the step files. [Yours, 20 Oct 2026; revised 23 Oct 2026]

## 21. Sector preferences [Yours]
Prefer bottleneck-solving industrial supply-chain sectors in India: BESS and pumped storage hydro, Stage 2 nuclear (fast breeder reactors), semiconductor manufacturing and 5-axis CNC import substitution, naval defence engineering, data-centre infrastructure, circular-economy materials recycling. Start research with sectors that have strong tailwinds (now or upcoming) and no major headwinds; headwind sectors only for exceptional stocks.

---

## Sectors with notes (researched in depth, 23 Oct 2026)
| Sector | Companies the notes come from |
|---|---|
| Capital goods, engineering, EPC, process equipment, pumps, machine tools, cranes | ACE, ANUP, INOXINDIA, IONEXCHANG, JASH, KIRLOSBROS, KLBRENG-B, KPEL, MACPOWER, POWERMECH |
| Defence and railway electronics | DATAPATTNS, HBLENGINE, KRISHNADEF |
| IT services, software, CPaaS, engineering services | DSSL, MOLDTECH, NEWGEN, TANLA |
| Speciality and commodity chemicals, polymers | HSCL, NITTAGELA, PLASTIBLEN |
| Metal recycling | GRAVITA |
| Packaging | KNACK |
| Equipment rental | SANGHVIMOV |
| Healthcare services | JSLL |
| Financial services (non-lending: rating agencies) | ICRA |
| Retail (TV and online) | VAIBHAVGBL |

Not yet covered (general rules only, flagged when met): banks and NBFCs, insurance, AMCs and brokers, real estate, pharma, FMCG, autos, power utilities, telecom, metals and mining, cement, textiles, logistics.
