"""Shared, deterministic I/O for the ART403 corpus stages (Python 3.10+)."""
from __future__ import annotations
import hashlib, json, os, re, tempfile, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = ['painting_manuscript','architecture','sculpture_relief','decorative_object','textile','metalwork','print','photograph','theme_discourse','concept_term','exhibition_display']
TEXT_TYPES = {'theme_discourse','concept_term'}

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_text(path, text):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == text.encode('utf-8'):
        return
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text); tmp = f.name
    os.replace(tmp, path)

def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2)+'\n')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def slug(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',value).strip('-')

def index_rows():
    rows=[]; module=None; counts={}
    for line_no,line in enumerate((ROOT/'lecture_paintings.md').read_text().splitlines(),1):
        if line.startswith('## Lecture:'):
            pdf=line.split(': ',1)[1]; module=int(re.search(r'Module (\d+)',pdf)[1])
        if not re.match(r'^\|\s*\d+',line): continue
        cells=[v.strip() for v in line.strip('|').split('|')]
        if len(cells)!=5: raise ValueError(f'Bad table row at line {line_no}')
        page=int(cells[0]); key=(module,page); counts[key]=counts.get(key,0)+1
        rows.append(dict(row_id=f'm{module}-p{page:02d}-r{counts[key]:02d}',module=module,slide=page,
                         name=cells[1],artist_date=cells[2],heading=cells[3],notes=cells[4],
                         pdf=pdf,index_line=line_no,image=f'slides/module-{module}/page_{page}.png'))
    return rows
