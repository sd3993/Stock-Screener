# Annual-report statements (old annual reports as a source)

What is settled about old annual reports as a source of statements for years before screener's: their units and layouts, and the field definitions (screener's) that parsed and subagent-read values follow. How the scripts and the reading subagents work: `/workflow/ar_statements.md`.

## Units and layouts
- Unit: read it from the page head ("Rs. in lakhs", "Rs. '000", "Rupees", "` in Crore"; "`" is the rupee sign in old fonts). Convert to **Rs crore**: lakh ÷ 100, thousand ÷ 10,000, million ÷ 10, rupees ÷ 10,000,000. EPS stays in rupees per share.
- Old Schedule VI layout (to FY11): sources of funds (capital, reserves, loan funds, deferred tax) = application of funds (fixed assets, investments, current assets less current liabilities and provisions). Schedule III (FY12 on): equity and liabilities = assets.

## Fields (screener's definitions)
| field | what to write |
|---|---|
| `sales` | Revenue from operations net of excise duty (sales/income from operations less excise; several operating income lines are added up). Banks: interest earned. |
| `other_income` | Other income, including interest and dividend income shown separately, as printed. Exceptional items are added here by the script, so write other income without them and put them in `exceptional`. |
| `exceptional` | Exceptional / extraordinary items before tax (income +, expense −), if printed; else omit. |
| `interest` | Interest / finance costs (net, as printed). Banks: interest expended. |
| `dep` | Depreciation and amortisation charged to the P&L (net of any transfer from revaluation reserve). |
| `pbt` | Profit before tax (after exceptional items). |
| `tax` | Total tax expense (current + deferred + fringe benefit + earlier years − MAT credit); positive for a charge. |
| `pat` | Profit after tax, before minority interest and before share of associates if shown after it (consolidated). |
| `eps` | Basic EPS in rupees, as printed. |
| `dividend` | Equity dividend for the year (interim + proposed final), excluding dividend tax and preference dividend; 0 when the report shows none (say where you looked: appropriation section, reserves note, directors' report). |
| `equity_cap` | Equity share capital (paid-up). |
| `reserves` | Reserves and surplus (other equity), plus share warrants / share application money if shown in shareholders' funds. Negative P&L debit balance shown on the assets side is subtracted. |
| `borrowings` | All loans: secured + unsecured loans (old layout), or long-term + short-term borrowings (new layout; current maturities of long-term debt sit in other current liabilities: add them and say so). Banks: deposits + borrowings. 0 when no loan line exists. |
| `total_assets` | Balance-sheet total. Old layout: total of sources of funds + current liabilities and provisions (= fixed assets + investments + current assets, loans and advances + misc. expenditure not written off). New layout: the total as printed. |
| `debtors` | Sundry debtors / trade receivables (net). |
| `cfo` | Net cash from operating activities (cash flow statement, total "A"). |
| `year_end` | Only when the queue lists it: the year end the statements are for (`YYYY-MM`). |
