"""Small authoring helpers for manually checked web evidence and glossary notes."""
import importlib.util
from common import ROOT
SOURCES={}; FEATURES=[]; VERIFICATIONS=[]

def S(key,title,url,batch,scope,method='search_excerpt'):
    if key in SOURCES: raise ValueError(f'Duplicate source {key}')
    SOURCES[key]=dict(id=key,title=title,url=url,retrieved='2026-11-22',
        retrieval_method=method,research_log=f'corpus_data/research_logs/{batch}.txt',support_scope=scope)

def F(key,title,note,dist,sources='',search='',aliases='',status=None):
    FEATURES.append(dict(id=key,title=title,grounded_significance=note,distinctions=[dist],
        source_ids=sources.split(),research_logs=search.split(),aliases=aliases.split('|') if aliases else [],
        status=status or ('sourced' if sources else 'draft')))

def V(entity,note,sources,kind='verification',resolves=None):
    VERIFICATIONS.append(dict(entity_id=entity,note=note,source_ids=sources.split(),kind=kind,resolves=resolves or []))

def load_research():
    SOURCES.clear();FEATURES.clear();VERIFICATIONS.clear()
    for p in sorted((ROOT/'corpus_data/grounding').glob('*.py')):
        spec=importlib.util.spec_from_file_location('ground_'+p.stem,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return SOURCES,FEATURES,VERIFICATIONS
