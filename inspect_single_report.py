import os
from bs4 import BeautifulSoup

report_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\Report_Single_Test.html"

with open(report_path, "r", encoding="utf-16", errors="ignore") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
rows = soup.find_all("tr")

for r in rows:
    cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
    if len(cols) >= 2:
        print("COLS:", cols)
