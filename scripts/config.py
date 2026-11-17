import glob, os
# Shared paths for the scripts. The run folder is the RUN environment variable if set,
# else RUN below, else the newest runs/FY* folder (run-folder layout: workflow/WORKFLOW.md). Run every script from the project root.
# Every run-folder, shared-run-file and company-output path the scripts use comes from the functions below, so a layout
# change is one edit here (/COMMON_AI.md: data/ = reusable facts; runs/ = predictive or judgement outputs).
RUN = 'FY27Q2'  # e.g. 'FY27Q2' or 'FY27Q2_full'; set at run start (S1)
RUNS_DIR = 'runs'


def run_dir():
    r = os.environ.get('RUN') or RUN
    if r:
        return os.path.join(RUNS_DIR, r)
    runs = sorted(d for d in glob.glob(os.path.join(RUNS_DIR, 'FY*')) if os.path.isdir(d))
    if not runs:
        raise SystemExit('no run folder: create runs/<FYyyQn>/ and set RUN in scripts/config.py')
    return runs[-1]


def run_path(name):
    """A run folder by name (FY27Q2, FY27Q2_full)."""
    return os.path.join(RUNS_DIR, name)


def all_runs():
    return sorted(d for d in glob.glob(os.path.join(RUNS_DIR, 'FY*')) if os.path.isdir(d))


def shared_path(name):
    """A file shared across runs: sector_calls.csv, sector_marker_states.csv, verdict_history.csv."""
    return os.path.join(RUNS_DIR, name)


def company_runs_dir(sym=''):
    """runs/companies/<SYM>/: a company's judgement outputs across runs (its thesis, marker-check history, analyses)."""
    return os.path.join(RUNS_DIR, 'companies', sym) if sym else os.path.join(RUNS_DIR, 'companies')


def thesis_path(sym):
    """A company's current thesis markers (S12 thesis.py register; S9 thesis.py check)."""
    return os.path.join(company_runs_dir(sym), 'thesis.json')


def marker_history_path(sym):
    """A company's marker-check history: every S9 check appended."""
    return os.path.join(company_runs_dir(sym), 'marker_checks.csv')


def analysis_dir(sym, results_quarter):
    """A company's deep analysis and its rechecks (S11): one folder per results quarter the analysis used (FYyyQn)."""
    return os.path.join(company_runs_dir(sym), results_quarter)


def analysis_dirs(sym):
    """A company's analysis folders, oldest first; the last holds the latest analysis."""
    import re
    d = company_runs_dir(sym)
    return sorted(os.path.join(d, x) for x in (os.listdir(d) if os.path.isdir(d) else ())
                  if re.match(r'^FY\d{2}Q[1-4]$', x) and os.path.isdir(os.path.join(d, x)))


# One folder per company: documents in quarter subfolders, screener answers in scr/, index/facts at the top.
COMPANIES_DIR = os.path.join('data', 'companies')


PLAYBOOK_DIR = os.path.join('data', 'playbook')

def playbook_dir():
    # The folder of the market-wide price and valuation history that S4 reads: the PLAYBOOK_DATA environment variable
    # (a folder path) if set, else data/playbook.
    h = os.environ.get('PLAYBOOK_DATA') or PLAYBOOK_DIR
    if not os.path.isdir(h):
        raise SystemExit(f'no market-wide history folder: {h} (set PLAYBOOK_DATA, or create data/playbook)')
    return h
