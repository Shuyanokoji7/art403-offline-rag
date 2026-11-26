"""Readable navigation for the finished corpus, outside the article manifest."""
from common import ROOT,read_json,write_text

def build():
    entries=read_json(ROOT/'corpus_data/article_catalogue.json')
    lines=['# ART403 article index','','[Readme](README_CORPUS.md) · [Quality report](QUALITY_REPORT.md) · [Manifest](manifest.csv)','',
           'Entity articles are placed in their earliest cited module. The manifest retains every recurrence. Draft labels identify unresolved evidence; sourced does not imply every caption was independently verified.','']
    for module in range(1,9):
        group=[a for a in entries if a['kind']=='entity' and a['path'].startswith(f'articles/module-{module}/')]
        lines += [f'## Module {module} — {len(group)} entity articles','','| Article | Type | Status | Cited slides |','|---|---|---|---|']
        for a in group:
            refs=', '.join(f"M{r['module']}:{r['slide']}" for r in a['references'])
            lines.append(f"| [{a['title']}](<{a['path']}>) | {a['type']} | {a['status']} | {refs} |")
        lines.append('')
    lines += ['## Shared features','','| Feature | Status | Connected entities |','|---|---|---:|']
    for a in entries:
        if a['kind']=='feature':lines.append(f"| [{a['title']}](<{a['path']}>) | {a['status']} | {len(a['related'])} |")
    write_text(ROOT/'CORPUS_INDEX.md','\n'.join(lines)+'\n')

if __name__=='__main__':build()
