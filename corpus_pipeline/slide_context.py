"""Gather lecture neighbours before analysis; arguments are authored, never guessed.

A blank index heading continues the previous explicit heading in that module.
This is marked as inherited, not misrepresented as printed on the slide itself.
"""
import importlib.util
from collections import defaultdict
from common import ROOT,digest

def arguments():
    path=ROOT/'corpus_data/editorial/slide_arguments.py'
    spec=importlib.util.spec_from_file_location('slide_arguments',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.ARGUMENTS

def gather(entities,interpretations=None):
    interpretations=arguments() if interpretations is None else interpretations
    slides=defaultdict(set);explicit=defaultdict(list);by_id={e['id']:e for e in entities}
    for e in entities:
        for ref in e['references']:slides[ref['module'],ref['slide']].add(e['id'])
        for row in e['source_rows']:
            h=row.get('heading','—')
            if h!='—' and h not in explicit[row['module'],row['slide']]:explicit[row['module'],row['slide']].append(h)
    effective={};origins={};groups=defaultdict(set)
    for module in sorted({m for m,p in slides}):
        last=[];origin=None
        for page in range(1,max(p for m,p in slides if m==module)+1):
            if explicit[module,page]:last=explicit[module,page];origin=page
            effective[module,page]=list(last);origins[module,page]=origin
            for h in last:groups[module,h].update(slides[module,page])
    result={}
    for e in entities:
        contexts=[];all_peers=set()
        for ref in e['references']:
            key=(ref['module'],ref['slide']);m,p=key
            same=slides[key]-{e['id']};headings=effective[key]
            peers=set().union(*(groups[m,h] for h in headings)) if headings else set()
            peers.discard(e['id']);adjacent=(slides[m,p-1]|slides[m,p+1])-{e['id']}
            selected=same|peers|adjacent;all_peers|=selected
            arg=interpretations.get(f'{m}:{p}')
            if not arg:raise ValueError(f'Missing authored slide argument: M{m}:{p}')
            contexts.append(dict(module=m,slide=p,headings=headings,heading_from_slide=origins[key],
                heading_inherited=bool(headings and origins[key]!=p),same_slide_ids=sorted(same),
                same_heading_ids=sorted(peers),adjacent_slide_ids=sorted(adjacent),
                argument=arg if arg.startswith('Course reading:') else 'Course reading: '+arg))
        # Neighbour context changes invalidate the cached interpretation too.
        peer_data=[{'id':ident,'name':by_id[ident]['name'],'type':by_id[ident]['type'],
            'source_rows':by_id[ident]['source_rows'],'references':by_id[ident]['references']} for ident in sorted(all_peers)]
        result[e['id']]=dict(occurrences=contexts,peer_entities=peer_data,
            input_sha256=digest([contexts,peer_data]))
    return result
