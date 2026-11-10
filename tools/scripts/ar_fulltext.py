# Whole-report text for reading helpers, so they search it instead of reading PDFs: writes ar_FY<yy>_full.txt beside each report's _pages.txt in
# ar_helper_queue.csv, with '=== page N ===' markers. Plain curl and pdftotext, no model tokens. Resumable; one request at a time.
#   python -I tools/scripts/ar_fulltext.py --tmp <empty scratch folder> [--dir runs/study] [--limit N] [--gap 1.5]
# A report whose pages hold almost no text is scanned: the file says so on its first line and the helper reads the PDF's images.
import argparse, csv, glob, os, shutil, subprocess, time

a = argparse.ArgumentParser()
a.add_argument('--tmp', required=True)
a.add_argument('--dir', default=None)
a.add_argument('--limit', type=int, default=0)
a.add_argument('--gap', type=float, default=1.5)
a = a.parse_args()
D = a.dir or os.environ.get('STUDY') or os.path.join('runs', 'study')  # the study folder (config.hist_dir)
os.makedirs(a.tmp, exist_ok=True)
rows = list(csv.DictReader(open(os.path.join(D, 'ar_helper_queue.csv'), encoding='utf-8')))
done = scanned = failed = 0
t0 = time.time()
for r in rows:
    out = r['json'][:-5] + '_full.txt'  # beside the parse; page_text is empty for a report the parser found no pages in
    if os.path.exists(out) or not r['url'].lower().startswith('http'):
        continue
    if a.limit and done + failed >= a.limit:
        break
    pdf = os.path.join(a.tmp, 'r.pdf')
    if os.path.exists(pdf):
        os.remove(pdf)
    subprocess.run(['curl.exe', '-s', '-L', '--max-time', '180', '-o', pdf, r['url']], capture_output=True)
    ok = os.path.exists(pdf) and open(pdf, 'rb').read(5) == b'%PDF-'
    if ok:
        p = subprocess.run(['pdftotext', '-q', '-enc', 'UTF-8', '-layout', pdf, '-'], capture_output=True, timeout=600)
        pages = p.stdout.decode('utf-8', 'replace').split('\f')
        ok = len(pages) > 1
    if not ok:
        failed += 1
        print(f"failed: {r['sym']} FY{r['fy']} {r['url']}", flush=True)
        time.sleep(a.gap)
        continue
    chars = sum(len(x.strip()) for x in pages)
    head = ''
    if chars < 100 * len(pages):
        head = 'SCANNED: almost no text in this PDF; read its pages as images\n'
        scanned += 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out + '.tmp', 'w', encoding='utf-8') as f:
        f.write(head + ''.join(f'=== page {i + 1} ===\n{x}\n' for i, x in enumerate(pages)))
    os.replace(out + '.tmp', out)
    done += 1
    if done % 25 == 0:
        print(f'{done} done, {scanned} scanned, {failed} failed, {time.time() - t0:.0f}s', flush=True)
    time.sleep(a.gap)
shutil.rmtree(a.tmp, ignore_errors=True)
print(f'finished: {done} written, {scanned} scanned, {failed} failed, {time.time() - t0:.0f}s of {len(rows)} in the queue', flush=True)
