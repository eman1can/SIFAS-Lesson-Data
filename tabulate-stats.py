"""
tabulate-stats.py — Convert every detail page in as-stats/ into 4 CSV files each.

Output layout (relative to this script):
  as-stats-csv/
    merged_drops/   {lesson_id}.csv   cols: img_id, name, rarity, sum, expectation
    item_drops/     {lesson_id}.csv   cols: img_id, name, amount, rarity, count, expectation
    insight_skills/ {lesson_id}.csv   cols: img_id, skill_id, name, count, expectation
    position_drops/ {lesson_id}.csv   cols: position, count, percentage

All Japanese names are translated to English.
"""

import csv
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

# --- Item names (drops) ---
ITEM_NAMES: dict[str, str] = {
    'スクールアイドルの証': 'School Idol Badge',
    # Voltage type books / seeds
    'ボルテージタイプのたね':  'Voltage Type Seed',
    'ボルテージタイプのつぼみ': 'Voltage Type Bud',
    'ボルテージタイプのわかば': 'Voltage Type Sprout',
    'ボルテージタイプのはな':  'Voltage Type Flower',
    'ボルテージタイプの入門書': 'Voltage Type Beginner Book',
    'ボルテージタイプの中級書': 'Voltage Type Intermediate Book',
    'ボルテージタイプの上級書': 'Voltage Type Advanced Book',
    'ボルテージタイプ秘伝の書': 'Voltage Type Secret Book',
    # SP type
    'SPタイプのたね':  'SP Type Seed',
    'SPタイプのつぼみ': 'SP Type Bud',
    'SPタイプのわかば': 'SP Type Sprout',
    'SPタイプのはな':  'SP Type Flower',
    'SPタイプの入門書': 'SP Type Beginner Book',
    'SPタイプの中級書': 'SP Type Intermediate Book',
    'SPタイプの上級書': 'SP Type Advanced Book',
    'SPタイプ秘伝の書': 'SP Type Secret Book',
    # Guard type
    'ガードタイプのたね':  'Guard Type Seed',
    'ガードタイプのつぼみ': 'Guard Type Bud',
    'ガードタイプのわかば': 'Guard Type Sprout',
    'ガードタイプのはな':  'Guard Type Flower',
    'ガードタイプの入門書': 'Guard Type Beginner Book',
    'ガードタイプの中級書': 'Guard Type Intermediate Book',
    'ガードタイプの上級書': 'Guard Type Advanced Book',
    'ガードタイプ秘伝の書': 'Guard Type Secret Book',
    # Skill type
    'スキルタイプのたね':  'Skill Type Seed',
    'スキルタイプのつぼみ': 'Skill Type Bud',
    'スキルタイプのわかば': 'Skill Type Sprout',
    'スキルタイプのはな':  'Skill Type Flower',
    'スキルタイプの入門書': 'Skill Type Beginner Book',
    'スキルタイプの中級書': 'Skill Type Intermediate Book',
    'スキルタイプの上級書': 'Skill Type Advanced Book',
    'スキルタイプ秘伝の書': 'Skill Type Secret Book',
    # Macarons
    '桃色のマカロン★1': 'Pink Macaron ★1',
    '桃色のマカロン★2': 'Pink Macaron ★2',
    '桃色のマカロン★3': 'Pink Macaron ★3',
    '紫色のマカロン★1': 'Purple Macaron ★1',
    '紫色のマカロン★2': 'Purple Macaron ★2',
    '紫色のマカロン★3': 'Purple Macaron ★3',
    '緑色のマカロン★1': 'Green Macaron ★1',
    '緑色のマカロン★2': 'Green Macaron ★2',
    '緑色のマカロン★3': 'Green Macaron ★3',
    '赤色のマカロン★1': 'Red Macaron ★1',
    '赤色のマカロン★2': 'Red Macaron ★2',
    '赤色のマカロン★3': 'Red Macaron ★3',
    '金色のマカロン★1': 'Gold Macaron ★1',
    '金色のマカロン★2': 'Gold Macaron ★2',
    '金色のマカロン★3': 'Gold Macaron ★3',
    '銀色のマカロン★1': 'Silver Macaron ★1',
    '銀色のマカロン★2': 'Silver Macaron ★2',
    '銀色のマカロン★3': 'Silver Macaron ★3',
    '青色のマカロン★1': 'Blue Macaron ★1',
    '青色のマカロン★2': 'Blue Macaron ★2',
    '青色のマカロン★3': 'Blue Macaron ★3',
    '黄色のマカロン★1': 'Yellow Macaron ★1',
    '黄色のマカロン★2': 'Yellow Macaron ★2',
    '黄色のマカロン★3': 'Yellow Macaron ★3',
}

# --- Skill name component translations ---
# Skill type (the leading word before the size bracket)
_SKILL_TYPE = {
    'アピール＋':      'Appeal+',
    'アピールUP':      'Appeal UP',
    'ボルテージ獲得':   'Voltage Gain',
    'ボルテージUP':    'Voltage UP',
    'クリティカル＋':   'Critical+',
    'クリティカルUP':   'Critical UP',
    'SP特技UP':       'SP Skill UP',
    'コンボ数UP':      'Combo Count UP',
    'シールド獲得':     'Shield Gain',
    'スタミナ回復':     'Stamina Recovery',
    'タイプ効果＋':     'Type Effect+',
    'ダメージ軽減':     'Damage Reduction',
    '特技発動率＋':     'Skill Rate+',
    '特技発動率UP':    'Skill Rate UP',
}

# Size bracket
_SIZE = {
    '[小]': '[S]',
    '[中]': '[M]',
    '[大]': '[L]',
    '[特]': '[SP]',
    '[極]': '[MAX]',
}

# Trigger (after ':')
_TRIGGER = {
    '30%達成時':  'at 30%',
    'AC成功時':   'on AC Success',
    'AC時':       'on AC',
    '曲開始時':   'at Song Start',
    '残80%時':    'at 80% Remaining',
}

# Target modifier (after '/')
_TARGET = {
    '全員':   'All',
    '同属性':  'Same Attribute',
    'タイプ':  'Type',
    '同作戦':  'Same Strategy',
    '同学年':  'Same Year',
    '同学校':  'Same School',
    '仲間':    'Buddy',
}

# Passive-only targets (appears after ':' with no trigger keyword — e.g. "アピール＋ [中]:タイプ")
_PASSIVE_TARGET = {**_TARGET}


def translate_skill(name: str) -> str:
    """
    Translate a Japanese insight skill name to English.
    Format:  SkillType [Size]               (passive, no condition)
             SkillType [Size]:Trigger       (all / no sub-target)
             SkillType [Size]:Trigger/Target
             SkillType [Size]:PassiveTarget  (passive with group)
    """
    # Try to match the full pattern
    m = re.fullmatch(
        r'(.+?)\s+(\[.\])'          # group 1: type, group 2: size
        r'(?::(.+?)(?:/(.+))?)?',   # optional :trigger(/target)
        name
    )
    if not m:
        return name  # unknown format — return as-is

    raw_type, raw_size, raw_cond, raw_target = m.group(1), m.group(2), m.group(3), m.group(4)

    en_type = _SKILL_TYPE.get(raw_type, raw_type)
    en_size = _SIZE.get(raw_size, raw_size)

    if raw_cond is None:
        return f'{en_type} {en_size}'

    # Is the condition a trigger keyword?
    if raw_cond in _TRIGGER:
        en_trigger = _TRIGGER[raw_cond]
        if raw_target:
            en_target = _TARGET.get(raw_target, raw_target)
            return f'{en_type} {en_size}: {en_trigger} / {en_target}'
        else:
            return f'{en_type} {en_size}: {en_trigger}'
    else:
        # Passive condition — it's actually a target
        en_target = _PASSIVE_TARGET.get(raw_cond, raw_cond)
        return f'{en_type} {en_size}: {en_target}'


def translate_item(name: str) -> str:
    return ITEM_NAMES.get(name, name)


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

IMG_ID_RE = re.compile(r'/images_b95/(\d+)\.png')

SECTIONS = ('drops_merged', 'drops', 'insight', 'pos')


class DetailParser(HTMLParser):
    """
    Parses one detail page and populates four lists of row-dicts:
      .merged_drops, .item_drops, .insight_skills, .position_drops
    """

    def __init__(self):
        super().__init__()
        self.merged_drops:   list[dict] = []
        self.item_drops:     list[dict] = []
        self.insight_skills: list[dict] = []
        self.position_drops: list[dict] = []

        self._section: str | None = None
        self._in_tbody = False
        self._in_tr = False
        self._in_td = False
        self._col = -1
        self._buf = ''
        self._img_id = ''
        self._current: dict = {}

    def handle_comment(self, tag):
        if tag.startswith('td') and tag.endswith('td'):
            if self._section == 'drops_merged':
                rarity, content_id, content_type = tag[3:-4].split('_')
                self._current['content_id'] = content_id
                self._current['content_type'] = content_type
            else:
                rarity, content_id, content_type, content_amount = tag[3:-4].split('_')
                self._current['content_id'] = content_id
                self._current['content_type'] = content_type

    # ------------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == 'div':
            id_ = attrs.get('id', '')
            if id_ in SECTIONS:
                self._section = id_
                self._in_tbody = False

        if tag == 'tbody':
            self._in_tbody = True

        if not self._in_tbody:
            return

        if tag == 'tr':
            self._in_tr = True
            self._col = -1
            self._current = {}

        if tag == 'td' and self._in_tr:
            self._col += 1
            self._in_td = True
            self._buf = ''
            self._img_id = ''

        if tag == 'img' and self._in_td:
            src = attrs.get('src', '')
            m = IMG_ID_RE.search(src)
            if m:
                self._img_id = m.group(1)

    # ------------------------------------------------------------------
    def handle_endtag(self, tag):
        if tag == 'tbody':
            self._in_tbody = False

        if tag == 'td' and self._in_td:
            self._flush_td()
            self._in_td = False

        if tag == 'tr' and self._in_tr:
            self._flush_row()
            self._in_tr = False
            self._current = {}

    # ------------------------------------------------------------------
    def handle_data(self, data):
        if self._in_td:
            self._buf += data

    # ------------------------------------------------------------------
    def _flush_td(self):
        text = self._buf.strip()
        sec = self._section
        col = self._col
        cur = self._current

        if sec == 'drops_merged':
            # cols: 0=icon(img), 1=name, 2=rarity, 3=sum, 4=expectation
            if col == 0:   cur['img_id'] = self._img_id
            elif col == 1: cur['name'] = translate_item(text)
            elif col == 2: cur['rarity'] = text
            elif col == 3: cur['content_amount'] = text
            elif col == 4: cur['expectation'] = text

        elif sec == 'drops':
            # cols: 0=icon, 1=name, 2=amount, 3=rarity, 4=count, 5=expectation
            if col == 0:   cur['img_id'] = self._img_id
            elif col == 1: cur['name'] = translate_item(text)
            elif col == 2: cur['content_amount'] = text
            elif col == 3: cur['rarity'] = text
            elif col == 4: cur['count'] = text
            elif col == 5: cur['expectation'] = text

        elif sec == 'insight':
            # cols: 0=icon, 1=skill_id, 2=name, 3=count, 4=expectation
            if col == 0:   cur['img_id'] = self._img_id
            elif col == 1: cur['skill_id'] = text
            elif col == 2: cur['name'] = translate_skill(text)
            elif col == 3: cur['count'] = text
            elif col == 4: cur['expectation'] = text

        elif sec == 'pos':
            # cols: 0=position, 1=count, 2=percentage
            if col == 0:   cur['position'] = text
            elif col == 1: cur['count'] = text
            elif col == 2: cur['percentage'] = text

    # ------------------------------------------------------------------
    def _flush_row(self):
        if not self._current:
            return
        sec = self._section
        if sec == 'drops_merged' and 'img_id' in self._current:
            self.merged_drops.append(self._current)
        elif sec == 'drops' and 'img_id' in self._current:
            self.item_drops.append(self._current)
        elif sec == 'insight' and 'skill_id' in self._current:
            self.insight_skills.append(self._current)
        elif sec == 'pos' and 'position' in self._current:
            self.position_drops.append(self._current)


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

MERGED_FIELDS   = ['name', 'id', 'rarity', 'sum', 'expectation']
DROPS_FIELDS    = ['content_id', 'content_type', 'content_amount', 'rarity', 'count', 'expectation', 'estimated_weight']
INSIGHT_FIELDS  = ['name', 'skill_id', 'count', 'expectation', 'estimated_weight']
POS_FIELDS      = ['position', 'count', 'percentage']


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base      = Path(__file__).parent / 'as-stats'
    out_root  = Path(__file__).parent / 'as-stats-csv'

    dirs = {
        'merged_drops':   out_root / 'merged_drops',
        'item_drops':     out_root / 'item_drops',
        'insight_skills': out_root / 'insight_skills',
        'position_drops': out_root / 'position_drops',
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    html_files = sorted(base.glob('*.html'))
    if not html_files:
        sys.exit(f'No .html files found in {base}')

    for i, html_path in enumerate(html_files, 1):
        lesson_id = html_path.stem           # e.g. "111"
        html = html_path.read_text(encoding='utf-8', errors='replace')

        parser = DetailParser()
        parser.feed(html)

        n_item_drops = sum([int(x['count']) for x in parser.item_drops])
        for ix in range(len(parser.item_drops)):
            parser.item_drops[ix]['estimated_weight'] = int(parser.item_drops[ix]['count']) / n_item_drops * 10000

        n_insight_skills = sum([int(x['count']) for x in parser.insight_skills])
        for ix in range(len(parser.insight_skills)):
            parser.insight_skills[ix]['estimated_weight'] = int(parser.insight_skills[ix]['count']) / n_insight_skills * 10000

        write_csv(dirs['merged_drops']   / f'{lesson_id}.csv', MERGED_FIELDS,  parser.merged_drops)
        write_csv(dirs['item_drops']     / f'{lesson_id}.csv', DROPS_FIELDS,   parser.item_drops)
        write_csv(dirs['insight_skills'] / f'{lesson_id}.csv', INSIGHT_FIELDS, parser.insight_skills)
        write_csv(dirs['position_drops'] / f'{lesson_id}.csv', POS_FIELDS,     parser.position_drops)

        if i % 100 == 0 or i == len(html_files):
            print(f'  [{i}/{len(html_files)}] {lesson_id}.html done')

    print(f'\nAll done — {len(html_files)} lessons × 4 CSVs → {out_root}')


if __name__ == '__main__':
    main()
