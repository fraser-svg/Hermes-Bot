"""Render a standalone HTML file to PDF via Playwright chromium."""
from __future__ import annotations

import sys
from pathlib import Path

CSS = """
<style>
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
       color: #111; max-width: 780px; margin: 32px auto; line-height: 1.45;
       font-size: 12px; padding: 0 24px; }
h1 { font-size: 22px; margin-top: 0; border-bottom: 2px solid #111; padding-bottom: 4px; }
h2 { font-size: 16px; margin-top: 28px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
h3 { font-size: 13px; margin-top: 18px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; font-size: 10.5px; }
th, td { border: 1px solid #ccc; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #f4f4f4; }
code { background: #f2f2f2; padding: 1px 4px; border-radius: 3px; font-size: 10.5px; }
hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
em { color: #666; }
</style>
"""


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: md_to_pdf.py input.html output.pdf", file=sys.stderr)
        return 2
    src = Path(sys.argv[1]).resolve()
    dst = Path(sys.argv[2]).resolve()
    if dst.exists():
        print(f"refusing to overwrite {dst}", file=sys.stderr)
        return 2

    html = src.read_text()
    if "</head>" in html:
        html = html.replace("</head>", CSS + "</head>")
    else:
        html = CSS + html

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.pdf(
            path=str(dst),
            format="A4",
            margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            print_background=True,
        )
        browser.close()
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
