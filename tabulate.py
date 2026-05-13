"""
tabulate.py — Convert as-stats.loveliv.es.htm to a CSV file.

Output columns: lesson, l1_id, l1_name, l2_id, l2_name, l3_id, l3_name, count
  - lesson   : numeric lesson ID
  - lN_id    : image asset ID extracted from the img src URL (e.g. 636553)
  - lN_name  : Japanese skill name text
  - count    : number of times this lesson combination was recorded
"""

import csv
import re
import sys
from pathlib import Path
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# Minimal HTML parser (no third-party deps required)
# ---------------------------------------------------------------------------

class Row:
    __slots__ = ("lesson", "l1_id", "l1_name", "l2_id", "l2_name",
                 "l3_id", "l3_name", "count")

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, "")


IMG_ID_RE = re.compile(r"/images_b95/(\d+)\.png")


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[Row] = []

        # state
        self._in_tbody = False
        self._in_tr = False
        self._td_index = -1          # which <td> inside current <tr> (0-based)
        self._in_td = False
        self._in_lesson_span = False
        self._current_row: Row | None = None
        self._capture_text = False   # are we collecting text content?
        self._text_buf = ""          # accumulated text inside a <td>
        self._pending_img_id = ""    # img id seen in current <td>

    # ------------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "tbody":
            self._in_tbody = True
            return

        if not self._in_tbody:
            return

        if tag == "tr":
            self._in_tr = True
            self._td_index = -1
            self._current_row = Row()
            return

        if not self._in_tr:
            return

        if tag == "td":
            self._td_index += 1
            self._in_td = True
            self._text_buf = ""
            self._pending_img_id = ""
            # columns 1-3 (L1/L2/L3) need text capture; others too
            self._capture_text = self._td_index in (0, 1, 2, 3, 4)
            return

        if tag == "span" and self._in_td and self._td_index == 0:
            self._in_lesson_span = True
            return

        if tag == "img" and self._in_td and self._td_index in (1, 2, 3):
            src = attrs.get("src", "")
            m = IMG_ID_RE.search(src)
            if m:
                self._pending_img_id = m.group(1)
            return

    # ------------------------------------------------------------------
    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
            return

        if tag == "span" and self._in_lesson_span:
            self._in_lesson_span = False
            return

        if tag == "td" and self._in_td:
            text = self._text_buf.strip()
            r = self._current_row
            if self._td_index == 0:
                r.lesson = text
            elif self._td_index == 1:
                r.l1_id = self._pending_img_id
                r.l1_name = text
            elif self._td_index == 2:
                r.l2_id = self._pending_img_id
                r.l2_name = text
            elif self._td_index == 3:
                r.l3_id = self._pending_img_id
                r.l3_name = text
            elif self._td_index == 4:
                r.count = text
            self._in_td = False
            self._capture_text = False
            return

        if tag == "tr" and self._in_tr:
            if self._current_row and self._current_row.lesson:
                self.rows.append(self._current_row)
            self._in_tr = False
            self._current_row = None
            return

    # ------------------------------------------------------------------
    def handle_data(self, data):
        if self._capture_text and self._in_td:
            # Skip text inside a nested <a> for the Link column (td_index==5)
            self._text_buf += data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    htm_path = Path(__file__).parent / "as-stats-page" / "as-stats.loveliv.es.htm"
    csv_path = Path(__file__).parent / "as-stats.csv"

    if not htm_path.exists():
        sys.exit(f"Error: cannot find {htm_path}")

    html = htm_path.read_text(encoding="utf-8", errors="replace")

    parser = TableParser()
    parser.feed(html)

    fieldnames = ["lesson", "l1_id", "l1_name", "l2_id", "l2_name",
                  "l3_id", "l3_name", "count"]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in parser.rows:
            writer.writerow({
                "lesson":   row.lesson,
                "l1_id":    row.l1_id,
                "l1_name":  row.l1_name,
                "l2_id":    row.l2_id,
                "l2_name":  row.l2_name,
                "l3_id":    row.l3_id,
                "l3_name":  row.l3_name,
                "count":    row.count,
            })

    print(f"Written {len(parser.rows)} rows → {csv_path}")


if __name__ == "__main__":
    main()
