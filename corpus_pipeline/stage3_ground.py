"""Assemble fetched-source research; cache features and each entity's evidence links.

Research is curated in corpus_data/grounding, with retrieval receipts and explicit
support scopes. A missing researched feature is an error, never silently dropped.
"""
from collections import defaultdict
from common import ROOT, digest, read_json, write_json
from research_schema import load_research
import importlib.util

VERSION='art403-grounding-2.0'

def cached(path,key,result):
    old=read_json(path) if path.exists() else {}
    if old.get('input_sha256')==key and old.get('status')=='complete': return old['result'],True
    write_json(path,dict(input_sha256=key,status='complete',result=result));return result,False

def build():
    analyses=read_json(ROOT/'visual_analysis.json');sources,features,verifications=load_research()
    spec=importlib.util.spec_from_file_location('feature_distractors',ROOT/'corpus_data/editorial/feature_distractors.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if set(module.CLAIMS)!=set(module.CORRECTIONS) or set(module.CLAIMS)!={f['id'] for f in features}:raise ValueError('Shared feature distractor/correction coverage')
    by_id={a['id']:a for a in analyses}; occurrences=defaultdict(list)
    for a in analyses:
        for feature in a['feature_ids']:
            occurrences[feature].append(dict(entity_id=a['id'],title=a['name'],type=a['type'],
                references=[{'module':r['module'],'slide':r['slide']} for r in a['lecture_references']],
                relation='Flagged in the entity review: may be a visible motif, technique, interpretive context or explicit comparison; not necessarily a literal depicted object.',
                analysis_sha256=a['input_sha256'],slide_context=[{k:c[k] for k in ('module','slide','argument')} for c in a['slide_context']['occurrences']]))
    if len({f['id'] for f in features})!=len(features): raise ValueError('Duplicate feature IDs')
    if set(occurrences)!={f['id'] for f in features}: raise ValueError('Feature coverage mismatch')
    for source in sources.values():
        if not (ROOT/source['research_log']).exists(): raise ValueError(f'Missing retrieval receipt: {source["id"]}')
    glossary=[];counts={'features_built':0,'features_cached':0,'entities_built':0,'entities_cached':0}
    for f in sorted(features,key=lambda x:x['id']):
        if f['status']=='sourced' and not f['source_ids']: raise ValueError(f['id'])
        citations=[sources[k] for k in f['source_ids']]
        logs=sorted(set(f['research_logs']+[s['research_log'] for s in citations]))
        logs=[p if '/' in p else f'corpus_data/research_logs/{p}.txt' for p in logs]
        if not logs or any(not (ROOT/p).exists() for p in logs): raise ValueError(f'No research attempt: {f["id"]}')
        result={**f,'sources':citations,'research_logs':logs,'occurrences':occurrences[f['id']],
                'entity_ids':[o['entity_id'] for o in occurrences[f['id']]],
                'distractor':{'claim':module.CLAIMS[f['id']],'why_wrong':module.CORRECTIONS[f['id']]},
                'evidence_limit':'Source scope applies to the shared note. Comparative sources do not verify every linked object’s identity, date or provenance.'}
        result,hit=cached(ROOT/'corpus_cache/stage3/features'/f'{f["id"]}.json',digest([VERSION,result]),result)
        counts['features_cached' if hit else 'features_built']+=1;glossary.append(result)
    by_feature={f['id']:f for f in glossary};v_by_id=defaultdict(list)
    for v in verifications:
        if v['entity_id'] not in by_id: raise ValueError(f'Unknown verification entity {v["entity_id"]}')
        if set(v['resolves'])-set(by_id[v['entity_id']]['uncertainties']): raise ValueError('Unknown resolved uncertainty')
        v_by_id[v['entity_id']].append({**v,'sources':[sources[k] for k in v['source_ids']]})
    entity_results=[]
    for a in analyses:
        fs=[by_feature[k] for k in a['feature_ids']];vs=v_by_id[a['id']]
        resolved={r for v in vs for r in v['resolves']}
        unresolved=[r for r in a['uncertainties'] if r not in resolved]
        related=sorted({e for f in fs for e in f['entity_ids']}-{a['id']})
        result=dict(id=a['id'],feature_ids=a['feature_ids'],related=related,verifications=vs,
                    unresolved_uncertainties=unresolved,resolved_uncertainties=sorted(resolved),
                    draft_feature_ids=[f['id'] for f in fs if f['status']=='draft'],
                    status='draft' if unresolved else 'sourced',
                    status_scope='Sourced means claims have a stated visual, lecture or external basis. It does not mean all object metadata has been independently verified. Shared draft-feature links retain their own warnings.')
        key=digest([VERSION,a,result,fs]);result,hit=cached(ROOT/'corpus_cache/stage3/entities'/f'{a["id"]}.json',key,result)
        counts['entities_cached' if hit else 'entities_built']+=1;entity_results.append(result)
    write_json(ROOT/'feature_glossary.json',glossary)
    write_json(ROOT/'corpus_data/entity_grounding.json',entity_results)
    write_json(ROOT/'corpus_data/sources.json',list(sources.values()))
    write_json(ROOT/'corpus_data/validation/stage3_run.json',counts)
    print(f'Stage 3: {len(glossary)} features, {len(entity_results)} entity evidence records; {counts}')

if __name__=='__main__':build()
