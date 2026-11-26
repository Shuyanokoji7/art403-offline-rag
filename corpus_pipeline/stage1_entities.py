"""Combine reviewed classifications, retaining every source row and occurrence."""
from collections import Counter
import re
from common import ROOT, TYPES, file_hash, index_rows, read_json, write_json
from review_schema import load_reviews

def build():
    rows=index_rows(); by_id={r['row_id']:r for r in rows}; seen=Counter(); entities=[]
    for review in load_reviews():
        selected=[by_id[x] for x in review['row_ids']]; seen.update(review['row_ids'])
        refs={(r['module'],r['slide']) for r in selected}
        refs.update((r['module'],r['slide']) for r in review['extra_slides'])
        references=[]
        for m,p in sorted(refs):
            pdf=next(ROOT.glob(f'ART403_Module {m}_*.pdf')).name
            image=f'slides/module-{m}/page_{p}.png'
            references.append(dict(module=m,slide=p,pdf=pdf,image=image,image_sha256=file_hash(ROOT/image),
                text=f'corpus_data/slide_text/module-{m}/page_{p}.txt'))
        # Only structured accession-looking values, not every parenthetical phrase.
        accessions=[]
        for r in selected:
            for token in re.findall(r'\(([^()]+)\)',r['notes']):
                if re.fullmatch(r'(?:[A-Z]+[ .,/-]*)?\d[\w., /-]*',token) and not re.fullmatch(r'\d{4}',token):
                    accessions.append(dict(value=token,row_id=r['row_id'],source='index notes'))
        entities.append(dict(id=review['id'],name=review['title'],type=review['type'],
            artist_date=list(dict.fromkeys(r['artist_date'] for r in selected if r['artist_date']!='—')),
            headings=list(dict.fromkeys(r['heading'] for r in selected if r['heading']!='—')),
            notes=[{'text':r['notes'],'row_id':r['row_id']} for r in selected],references=references,
            accession_numbers=accessions,source_rows=selected,
            classification_basis='Reviewed slide image and index context; text-only supplemental concepts use extracted slide text.',
            merge_basis='Same identified object, component, or curatorial display unit. Distinct indexed objects inside a display are retained as source_rows.',
            supplemental=not bool(selected)))
    missing=sorted(set(by_id)-set(seen)); duplicate=sorted(k for k,v in seen.items() if v!=1)
    if missing or duplicate: raise ValueError(f'Row coverage: missing={missing}, multiply assigned={duplicate}')
    ids=[e['id'] for e in entities]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate entity IDs')
    if any(e['type'] not in TYPES or not e['references'] for e in entities): raise ValueError('Invalid type/references')
    write_json(ROOT/'entities.json',entities)
    write_json(ROOT/'corpus_data/coverage_rows.json',{'input_rows':len(rows),'assigned_rows':len(seen),'entities':len(entities),'types':dict(Counter(e['type'] for e in entities)),'rows':{k:next(e['id'] for e in entities if any(r['row_id']==k for r in e['source_rows'])) for k in by_id}})
    print(f'{len(entities)} entities; all {len(rows)} input rows assigned exactly once.')

if __name__=='__main__': build()
