# Fetch learnings (one line per item; fetch subagents append, the orchestrator folds them into /workflow/s10_fetch.md, /principles/data_rules.md or a file in /sources/)
- **Scanned SME results:** some SME filers (SHERA) file a legible copy of their results minutes after the scanned one; scr_docs.py skips it, so look for it before reading page images.
- **NSE hosts in ad-hoc downloads:** rewrite nsearchives.nseindia.com to archives.nseindia.com, as scr_docs.py does (the former hung for over 2 minutes).
