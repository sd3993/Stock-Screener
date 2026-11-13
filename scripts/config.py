import glob, os
# Shared paths for the scripts. The run folder is the RUN environment variable if set,
# else RUN below, else the newest runs/FY* folder (run-folder layout: workflow/WORKFLOW.md). Run every script from the project root.
# Every run-folder, shared-run-file and company-output path the scripts use comes from the functions below, so a layout
# change is one edit here (/COMMON_AI.md: data/ = reusable facts; runs/ = predictive or judgement outputs).
RUN = ''  # e.g. 'FY27Q2' or 'FY27Q2_full'; set at run start (S1)
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
    """A company's current thesis markers (S14 thesis.py register; S11 thesis.py check)."""
    return os.path.join(company_runs_dir(sym), 'thesis.json')


def marker_history_path(sym):
    """A company's marker-check history: every S11 check appended."""
    return os.path.join(company_runs_dir(sym), 'marker_checks.csv')


def analysis_dir(sym, results_quarter):
    """A company's deep analysis and its rechecks (S13): one folder per results quarter the analysis used (FYyyQn)."""
    return os.path.join(company_runs_dir(sym), results_quarter)


def analysis_dirs(sym):
    """A company's analysis folders, oldest first; the last holds the latest analysis."""
    import re
    d = company_runs_dir(sym)
    return sorted(os.path.join(d, x) for x in (os.listdir(d) if os.path.isdir(d) else ())
                  if re.match(r'^FY\d{2}Q[1-4]$', x) and os.path.isdir(os.path.join(d, x)))


# One folder per company: documents in quarter subfolders, Tapetide answers in api/, index/facts at the top.
COMPANIES_DIR = os.path.join('data', 'companies')
MARKET_DIR = os.path.join('data', 'market')  # market-wide answers
CALL_LOG = os.path.join('data', 'calls.csv')

def api_path(sym, name):
    return os.path.join(MARKET_DIR, name + '.json') if sym in ('', '_market') else os.path.join(COMPANIES_DIR, sym, 'api', name + '.json')


PLAYBOOK_DIR = os.path.join('data', 'playbook')

def playbook_dir():
    # The playbook base data (market-wide history kept for the sector playbooks, workflow/s6_playbook.md): the
    # PLAYBOOK_DATA environment variable (a folder path) if set, else data/playbook.
    h = os.environ.get('PLAYBOOK_DATA') or PLAYBOOK_DIR
    if not os.path.isdir(h):
        raise SystemExit(f'no playbook base data folder: {h} (the playbook base data: workflow/s6_playbook.md)')
    return h


def playbook_sector_dir(sector):
    """A sector's playbook (S6-S7): episodes.csv, data.md, playbook.md, notes_proposed.md."""
    return os.path.join(os.environ.get('PLAYBOOK_DATA') or PLAYBOOK_DIR, 'sectors', sector)
