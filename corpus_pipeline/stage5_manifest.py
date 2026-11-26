"""Manifest and section-sized retrieval records with exact cl100k_base token counts."""
from __future__ import annotations
import csv,io,json,os,re,sys
from pathlib import Path
from common import ROOT,read_json,write_text,write_json,digest

def tokenizer():
    try:import tiktoken
    except ImportError:
        local=Path('/tmp/art403-corpus-libs')
        if local.exists():sys.path.insert(0,str(local))
        try:import tiktoken
        except ImportError:raise SystemExit('Install corpus_pipeline/requirements.txt; tiktoken is needed for exact counts.')
    os.environ.setdefault('TIKTOKEN_CACHE_DIR',str(ROOT/'corpus_data/tokenizer'))
    return tiktoken.get_encoding('cl100k_base')

def split_text(text,enc,limit=550):
    ids=enc.encode(text,disallowed_special=())
    if len(ids)<=limit:return [text]
    # Split on Unicode characters, retaining complete text and avoiding split UTF-8 bytes.
    chunks=[];start=0
    while start<len(text):
        lo=start+1;hi=len(text)
        while lo<hi:
            mid=(lo+hi+1)//2
            if len(enc.encode(text[start:mid],disallowed_special=()))<=limit:lo=mid
            else:hi=mid-1
        end=lo
        if end<len(text):
            boundary=max(text.rfind('\n',start,end),text.rfind('. ',start,end))
            if boundary>start+(end-start)//2:end=boundary+1
        chunks.append(text[start:end]);start=end
    return chunks

def evidence_metadata(section,analysis=None):
    if section in ('External Checks','Sources'):
        category='external_verification';tiers=[]
    elif section=='Lecture Evidence':
        category='raw_lecture_assertion';tiers=[]
    elif section=='Attribution Note':
        category='unresolved_external_attribution';tiers=[3]
    elif section in ('Slide Context','Context','Significance','Definition and Grounded Significance'):
        category='course_interpretation';tiers=[2]
    elif section=='Distinctions':
        category='exam_distractor_and_correction';tiers=[]
    elif section in ('Connected Features','Applied To'):
        category='cross_reference';tiers=[]
    else:
        category='curated_analysis'
        tiers=sorted({c['tier'] for c in (analysis or {}).get('claims',[]) if c['section']==section})
    return dict(evidence_category=category,confidence_tiers=tiers,confidence_tier_scope='section',
                contains_false_exam_claim=section=='Distinctions')

def build():
    enc=tokenizer();catalogue=read_json(ROOT/'corpus_data/article_catalogue.json')
    analyses={a['id']:a for a in read_json(ROOT/'visual_analysis.json')}
    output=io.StringIO(newline='');fields=['slug','type','status','source','lectures','slides','token_count','path','kind','tokenizer','draft_reasons']
    writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader();chunks=[];total=0
    for article in catalogue:
        text=(ROOT/article['path']).read_text();n=len(enc.encode(text,disallowed_special=()));total+=n
        refs=article['references'];slides=';'.join(f"M{r['module']}:{r['slide']}" for r in refs)
        writer.writerow(dict(slug=article['id'],type=article['type'],status=article['status'],source=article['source'],
            lectures=';'.join(map(str,sorted({r['module'] for r in refs}))),slides=slides,token_count=n,path=article['path'],
            kind=article['kind'],tokenizer=enc.name,draft_reasons=' | '.join(article['draft_reasons'])))
        body=text.split('---\n',2)[2];parts=re.split(r'^## (.+)\n',body,flags=re.M)
        for i in range(1,len(parts),2):
            section=parts[i];content=parts[i+1].strip()
            prefix=f"{article['title']} | {section}\n"
            for part_no,part in enumerate(split_text(content,enc),1):
                chunk_text=prefix+part
                chunks.append(dict(id=f"{article['id']}:{i//2+1}:{part_no}",article_id=article['id'],title=article['title'],
                    section=section,status=article['status'],type=article['type'],article_path=article['path'],
                    slides=slides,source=article['source'],text=chunk_text,
                    token_count=len(enc.encode(chunk_text,disallowed_special=())),
                    **evidence_metadata(section,analyses.get(article['id'])),
                    content_sha256=digest(chunk_text)))
    write_text(ROOT/'manifest.csv',output.getvalue())
    write_text(ROOT/'retrieval_chunks.jsonl',''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in chunks))
    write_json(ROOT/'corpus_data/validation/stage5_run.json',dict(articles=len(catalogue),article_tokens=total,
        chunks=len(chunks),tokenizer=enc.name,token_count_scope='Entire UTF-8 Markdown article including YAML frontmatter.',
        chunking='Headed sections, split at at most 550 content tokens; title/section prefix adds a small overhead. No embedding service used.'))
    print(f'Stage 5: {len(catalogue)} manifest rows; {total:,} article tokens; {len(chunks)} retrieval chunks ({enc.name}).')

if __name__=='__main__':build()
