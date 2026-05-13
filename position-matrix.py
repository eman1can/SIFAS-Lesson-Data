"""
position-matrix.py -- Collect position drop percentages across all lessons.

Output: as-stats-csv/position_matrix.csv
  Rows: one per lesson (sorted numerically by ID)
  Cols: id, 1, 2, 3, 4, 5, 6, 7, 8, 9
  Values: bare floats (e.g. "23.245365")
"""

import csv
from pathlib import Path

base = Path(__file__).parent / 'as-stats-csv' / 'position_drops'
out  = Path(__file__).parent / 'as-stats-csv' / 'position_matrix.csv'

POSITIONS = [str(p) for p in range(1, 10)]

rows = []
for csv_path in sorted(base.glob('*.csv'), key=lambda p: int(p.stem)):
    lesson_id = csv_path.stem
    pos_map = {}
    with open(csv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            pos_map[row['position']] = row['percentage'].rstrip('%')
    rows.append({'id': lesson_id, **{p: pos_map.get(p, '') for p in POSITIONS}})

with open(out, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['id'] + POSITIONS)
    writer.writeheader()
    writer.writerows(rows)

print(f'Written {len(rows)} rows to {out}')
