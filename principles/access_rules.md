# Access rules: sources, accounts and the sheet

Which sources a run depends on, how accounts and credentials are used, and what reaches the sheet. How to reach each source: `/sources/SOURCES.md`.

## Standing source and account invariants (read before any Kite use and any screener.in fetch)
- **Kite is read-only:** use the Kite CLI strictly read-only (holdings, positions, orders and trades lists, profile, margins, quotes). Never place, modify, cancel or delete any order of any type (regular, AMO, GTT, alerts, MF, conversions) or write anything else to the account, unless the user explicitly asks for that specific action in chat (3 Nov 2026).
- **screener.in is never skipped:** screener.in (through the screener library in scripts, `scr_company.py` and `scr_tool.py`) is needed for every stock. If it can't be reached, never skip it or do a step partially without it: try to restore it (check the script's error, the login, the rate limit), and if you can't, pause the steps that need it, tell the user and wait.

## Sources, accounts and the sheet
- **Kite is not a blocker:** if it's unavailable (e.g. not logged in during an unattended run), carry on with the last fetched holdings (`data/kite/holdings.csv`, or the sheet's Holdings tab) and come back to it later (holdings only change the amount left to reach each target, not the targets).
- **Holdings:** fetched from Zerodha Kite only: in full at the start of each run (S1), so holdings go through the normal process, and re-checked for new trades in S15. If the gate or S13 makes a holding a full exit, or S11 finds an integrity flag on one, tell the user straight away, without waiting for S15.
- **Credentials:** secrets the user has provided (in the environment or otherwise) may be used wherever they apply. The screener login is in the user-level environment configuration as `SCREENER_USERNAME` and `SCREENER_PASSWORD` (3 Nov 2026), and scripts use it with `--login`. The account is a throwaway; the user allowed changing its screener.in settings (such as its column set) to get data efficiently (3 Nov 2026).
- **Sheet:** final outcomes only; the user reads it only when told all changes are in place. Its layout, colours and which columns each step writes are in `/sources/sheet.md` and the step files.
- **Storage:** full company downloads (S12) only for companies on `company_list.csv`; earlier steps download only the documents they read.
