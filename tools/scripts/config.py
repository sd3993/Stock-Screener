import glob, os
# Shared paths for the scripts. The run folder is the RUN environment variable if set,
# else RUN below, else the newest runs/FY* folder (process/README.md, "Run folders"). Run every script from the project root.
RUN = ''  # e.g. 'FY27Q2' or 'FY27Q2_full'; set at run start (S1)

def run_dir():
    r = os.environ.get('RUN') or RUN
    if r:
        return os.path.join('runs', r)
    runs = sorted(d for d in glob.glob(os.path.join('runs', 'FY*')) if os.path.isdir(d))
    if not runs:
        raise SystemExit('no run folder: create runs/<FYyyQn>/ and set RUN in tools/scripts/config.py')
    return runs[-1]

# One folder per company: documents in quarter subfolders, Tapetide answers in api/, index/facts at the top.
COMPANIES_DIR = os.path.join('data', 'companies')
MARKET_DIR = os.path.join('data', 'market')  # market-wide Tapetide answers
CALL_LOG = os.path.join('data', 'calls.csv')

def api_path(sym, name):
    return os.path.join(MARKET_DIR, name + '.json') if sym in ('', '_market') else os.path.join(COMPANIES_DIR, sym, 'api', name + '.json')


STUDY_DIR = os.path.join('runs', 'study')

def hist_dir():
    # The multibagger study's data, kept for the sector playbooks (process/s6_playbook.md): the STUDY environment
    # variable (a folder path) if set, else runs/study.
    h = os.environ.get('STUDY') or STUDY_DIR
    if not os.path.isdir(h):
        raise SystemExit(f'no study folder: {h} (process/s6_playbook.md, "The study data")')
    return h
