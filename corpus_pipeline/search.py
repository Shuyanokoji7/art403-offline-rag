"""Offline lexical search over retrieval chunks; returns evidence, not generated answers."""
import argparse,json,re,sqlite3
from common import ROOT

def search(query,limit=6,sourced_only=False):
    db=sqlite3.connect(':memory:')
    db.execute('CREATE VIRTUAL TABLE chunks USING fts5(title, section, text, article_id UNINDEXED, status UNINDEXED, article_path UNINDEXED, slides UNINDEXED)')
    for line in (ROOT/'retrieval_chunks.jsonl').read_text().splitlines():
        c=json.loads(line);db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?)',tuple(c[k] for k in ('title','section','text','article_id','status','article_path','slides')))
    terms=re.findall(r'[^\W_]+',query,flags=re.U)
    if not terms:return []
    expression=' OR '.join('"'+w+'"' for w in terms)
    where=" AND section NOT IN ('Connected Features','Applied To','Connection Scope','Sources')"
    if sourced_only:where+=" AND status='sourced'"
    rows=db.execute('SELECT title,section,text,status,article_path,slides,bm25(chunks,5.0,2.0,1.0) FROM chunks WHERE chunks MATCH ?'+where+' ORDER BY 7 LIMIT ?',(expression,limit)).fetchall()
    return [dict(zip(('title','section','text','status','article_path','slides','score'),r)) for r in rows]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('query');p.add_argument('--limit',type=int,default=6);p.add_argument('--sourced-only',action='store_true');a=p.parse_args()
    print(json.dumps(search(a.query,a.limit,a.sourced_only),ensure_ascii=False,indent=2))
