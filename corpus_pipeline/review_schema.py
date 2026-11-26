"""Compact authoring API for reviewed, entity-specific annotations.

Reviews are data, never automatically inferred from filenames or keyword matches.
"""
import importlib.util
from common import ROOT, index_rows, slug, read_json

TYPE_CODES=dict(P='painting_manuscript',A='architecture',S='sculpture_relief',O='decorative_object',T='textile',M='metalwork',R='print',F='photograph',D='theme_discourse',C='concept_term',E='exhibition_display')
REVIEWS=[]

def A(refs,title,kind,fields,features='',sig='',dist='',compare=None,uncertain=None,slides='',identifier=None):
    rows=index_rows(); selected=[]; extra=[]
    for group in refs.split(';') if refs else []:
        m,parts=group.split(':'); m=int(m)
        for part in parts.split(','):
            page,r=part.split('.'); page=int(page)
            found=[x['row_id'] for x in rows if x['module']==m and x['slide']==page and (r=='*' or x['row_id'].endswith(f'r{int(r):02d}'))]
            if not found: raise ValueError(f'No rows: {group}/{part}')
            selected.extend(found)
    for group in slides.split(';') if slides else []:
        m,parts=group.split(':'); extra.extend({'module':int(m),'slide':int(p)} for p in parts.split(','))
    significance={}
    for item in sig.split('|') if sig else []:
        k,v=item.split('=',1); significance[k]=v
    REVIEWS.append(dict(id=identifier or slug(title),title=title,type=TYPE_CODES[kind],row_ids=selected,
        sections=fields,feature_ids=features.split(),significance=significance,
        distinctions=[d.strip() for d in dist.split('|') if d.strip()],comparisons=compare or [],
        uncertainties=uncertain or [],extra_slides=extra))

def load_reviews():
    REVIEWS.clear()
    for path in sorted((ROOT/'corpus_data/reviews').glob('module*.py')):
        spec=importlib.util.spec_from_file_location('review_'+path.stem,path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    overrides=ROOT/'corpus_data/revisions/confidence-v2/pilot.json'
    if overrides.exists():
        by_id={r['id']:r for r in REVIEWS}
        for p in read_json(overrides):
            r=by_id[p['id']]
            r.update(title=p['title'],type=p['type'],sections=p['sections'],significance=p['significance'],
                uncertainties=p['unknown_facts'],distractor=p['distractor'],pilot_slide_context=p['slide_context'],
                tier1_fields=[k for k in p['sections'] if k!='Course Identification'])
            r['feature_ids']=list(dict.fromkeys(r['feature_ids']+['maritime-networks','craft-agency']))
    refinements=ROOT/'corpus_data/editorial/refinements.py'
    if refinements.exists():
        spec=importlib.util.spec_from_file_location('editorial_refinements',refinements)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        by_id={r['id']:r for r in REVIEWS}
        for ident,edit in module.REFINEMENTS.items():
            r=by_id[ident]
            for heading,body in edit['sections'].items():
                if body is None:r['sections'].pop(heading,None)
                else:r['sections'][heading]=body
            r['additional_attribution_gaps']=edit['unknown']
    return REVIEWS
