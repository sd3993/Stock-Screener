#!/usr/bin/env python
"""Turns a scanned annual report into images a subagent can read (no pdftoppm on this machine).
Downloads with plain curl into --dir (its own new folder), then:
  --sheets        contact sheets of the whole report (sheet_001.png ...), each thumbnail labelled with its PDF
                  page number, to find the statement pages cheaply
  --pages 40-44,60  those pages at reading size (p0040.png ...)
Run: uvx --with pypdfium2 --with pillow python -I scripts/ar_pdf_pages.py --url URL --dir FOLDER --sheets
"""
import argparse, os, subprocess, sys
if not {'-h', '--help'} & set(sys.argv[1:]):  # --help works without the uvx-only libraries
    import pypdfium2
    from PIL import ImageDraw

COLS, ROWS, THUMB_W = 6, 4, 260


def parse_pages(spec):
    out = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        out.extend(range(int(a), int(b or a) + 1))
    return out


def render(doc, n, width):
    page = doc[n - 1]
    scale = width / page.get_size()[0]
    return page.render(scale=scale).to_pil().convert('L')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', required=True, help='the report PDF (required)')
    ap.add_argument('--dir', required=True, help='its own new folder for the PDF and images (required)')
    ap.add_argument('--sheets', action='store_true', help='contact sheets of the whole report (sheet_001.png ...)')
    ap.add_argument('--pages', help='pages at reading size, e.g. 40-44,60 (p0040.png ...)')
    ap.add_argument('--width', type=int, default=1400, help='pixel width of a reading page (default: %(default)s)')
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    pdf = os.path.join(a.dir, 'r.pdf')
    if not os.path.exists(pdf):
        subprocess.run(['curl.exe', '-s', '-L', '--max-time', '180', '-o', pdf, a.url], capture_output=True)
    if not os.path.exists(pdf) or open(pdf, 'rb').read(5) != b'%PDF-':
        sys.exit(f'not a PDF: {a.url}')
    doc = pypdfium2.PdfDocument(pdf)
    total = len(doc)
    print('pages', total)
    if a.sheets:
        for s in range(0, total, COLS * ROWS):
            nums = range(s + 1, min(s + COLS * ROWS, total) + 1)
            thumbs = [render(doc, n, THUMB_W) for n in nums]
            h = max(t.size[1] for t in thumbs)
            sheet = thumbs[0].copy().resize((COLS * THUMB_W, ROWS * h))
            sheet.paste(255, (0, 0, COLS * THUMB_W, ROWS * h))
            draw = ImageDraw.Draw(sheet)
            for i, (n, t) in enumerate(zip(nums, thumbs)):
                x, y = (i % COLS) * THUMB_W, (i // COLS) * h
                sheet.paste(t, (x, y))
                draw.rectangle((x, y, x + 44, y + 14), fill=0)
                draw.text((x + 3, y + 2), str(n), fill=255)
            name = os.path.join(a.dir, f'sheet_{s // (COLS * ROWS) + 1:03d}.png')
            sheet.save(name)
            print(name, f'pages {nums[0]}-{nums[-1]}')
    if a.pages:
        for n in parse_pages(a.pages):
            if 1 <= n <= total:
                name = os.path.join(a.dir, f'p{n:04d}.png')
                render(doc, n, a.width).save(name)
                print(name)


if __name__ == '__main__':
    main()
