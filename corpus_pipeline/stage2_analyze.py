"""Assemble vision-reviewed annotations; queue changed inputs rather than inventing a new vision pass.

The actual first-pass vision review was performed interactively in this Codex
session. This script consumes the authored reviews and their immutable input
attestation. It does NOT call an image model or manufacture visual observations.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from common import ROOT, TEXT_TYPES, digest, read_json, write_json, file_hash
from review_schema import load_reviews
from analysis_schema import FIELDS, ALIASES, SCHEMA_VERSION, SIGNIFICANCE_DIMENSIONS, RELATIONSHIPS
from confidence import clean_sections,course,attribution_note,load_distractors
from slide_context import gather

CACHE=ROOT/'corpus_cache/stage2'
ATTESTATION=ROOT/'corpus_data/validation/review_attestation.json'

def request_for(entity,slide_context=None):
    text_only=entity['type'] in TEXT_TYPES
    references=list(entity['references'])
    if slide_context:
        references.extend(r for peer in slide_context['peer_entities'] for r in peer.get('references',[]))
    return dict(id=entity['id'],schema_version=SCHEMA_VERSION,entity=entity,
        image_inputs=[] if text_only else list(dict.fromkeys(r['image'] for r in references)),
        field_menu=FIELDS[entity['type']],omit_empty_fields=True,text_only=text_only,slide_context=slide_context,
        brief='First read every supplied same-slide and same-heading neighbour, including adjacent slides. State the grouping argument in Slide Context. Tier 1: state visible shape, colour, composition and contents plainly. Tier 2: prefix lecture-supported interpretation with Course reading:. Tier 3: consolidate unsupported external dates, makers, origins and identities in one Attribution Note; use not established at most once. The type brief is a menu: omit empty or inapplicable sections. Use decorative_object for standalone ceramic, ivory, glass, lacquer or enamel objects. Keep separate significance dimensions and subject versus medium origin where relevant. End with one specific plausible exam distractor and its correction, plus labelled comparisons. Use native crops for small details; do not invent a repeated motif merely because objects share a slide.')

def normalized_sections(review):
    out={ALIASES.get(k,k):v for k,v in review['sections'].items()}
    if 'Function & Circulation' in out:
        out.setdefault('Function',out['Function & Circulation']);out.setdefault('Circulation',out.pop('Function & Circulation'))
    if review['type']=='photograph':
        parts=[out.pop(k) for k in ['Subject','What It Is Evidence Of'] if k in out]
        if parts: out['Subject & Evidence']=' '.join(parts)
    return out

def build(prepare_only=False):
    entities=read_json(ROOT/'entities.json');review_list=load_reviews();reviews={r['id']:r for r in review_list}
    contexts=gather(entities);distractors=load_distractors(review_list)
    policy=digest([file_hash(__file__),*(file_hash(Path(__file__).with_name(name)) for name in ('confidence.py','slide_context.py','analysis_schema.py','editorial_rules.md'))])
    attestation=read_json(ATTESTATION) if ATTESTATION.exists() else {'entities':{}}
    results=[]; pending=[]; hits=0; built=0
    for entity in entities:
        ident=entity['id']; review=reviews.get(ident); slide_context=contexts[ident];req=request_for(entity,slide_context)
        for ref in entity['references']:
            if file_hash(ROOT/ref['image'])!=ref['image_sha256']:
                raise ValueError(f'Stale entities.json image hash: {ref["image"]}; rerun Stage 1.')
        proof=attestation['entities'].get(ident,{})
        binding={'references':[{k:r[k] for k in ('module','slide','image','image_sha256')} for r in entity['references']],
                 'source_rows_sha256':digest(entity['source_rows'])}
        if not review or proof.get('input_sha256')!=digest(binding):
            write_json(ROOT/'corpus_cache/vision_requests'/f'{ident}.json',req)
            pending.append(ident);continue
        key=digest([SCHEMA_VERSION,policy,entity,review,proof,slide_context,distractors[ident]])
        path=CACHE/f'{ident}.json'
        old=read_json(path) if path.exists() else {}
        if old.get('input_sha256')==key and old.get('status')=='complete':
            results.append(old['result']);hits+=1;continue
        if prepare_only:
            write_json(ROOT/'corpus_cache/vision_requests'/f'{ident}.json',req);pending.append(ident);continue
        raw_sections=normalized_sections(review)
        sections,claims,gaps=clean_sections(review,raw_sections)
        coverage={field:('included' if field in sections else 'omitted') for field in FIELDS[entity['type']]}
        ordered={k:sections[k] for k in FIELDS[entity['type']] if k in sections}
        ordered.update({k:v for k,v in sections.items() if k not in ordered})
        for c in review['comparisons']:
            if c['relationship'] not in RELATIONSHIPS: raise ValueError(c)
        if any(k not in SIGNIFICANCE_DIMENSIONS for k in review['significance']): raise ValueError(ident)
        if not ordered: raise ValueError(f'No substantive sections: {ident}')
        context=None
        if entity['type'] not in TEXT_TYPES:
            context={'artist_date_as_indexed':entity['artist_date'],
                'historical_context_as_indexed':entity['headings'],
                'lecture_notes':entity['notes'], 'accession_numbers':entity['accession_numbers']}
        unknowns=attribution_note(review['uncertainties']+review.get('additional_attribution_gaps',[]),gaps)
        if review.get('pilot_slide_context'):slide_context={**slide_context,'pilot_summary':review['pilot_slide_context']}
        result=dict(id=ident,name=entity['name'],type=entity['type'],sections=ordered,field_coverage=coverage,
            context=context,slide_context=slide_context,claims=claims,
            confidence_tiers={'1':'Direct visual observation; stated plainly.','2':'Lecture-supported reading; prefixed Course reading:.','3':'Unsupported external fact; consolidated attribution note.'},
            significance={k:course(v) for k,v in review['significance'].items()},feature_ids=review['feature_ids'],
            comparisons=review['comparisons'],distinctions=[distractors[ident]],distractor=distractors[ident],
            uncertainties=review['uncertainties'],attribution_gaps=unknowns,removed_uncertainty_clauses=gaps,
            status='draft' if review['uncertainties'] else 'sourced',
            image_references=[] if entity['type'] in TEXT_TYPES else entity['references'],
            lecture_references=entity['references'],vision_method=attestation['method'],
            evidence_basis={'sections':'Retained in-session visual observations, edited into claim-level confidence tiers; no new full-corpus vision run is claimed.',
                'context':'Unaltered index assertions; no blanket independent verification.',
                'significance':'Course reading of visible/captioned evidence. External term meanings are grounded separately in Stage 3.',
                'slide_context':'All same-slide, same-heading and adjacent-slide entities gathered before analysis; authored grouping arguments.'},
            input_sha256=key)
        write_json(path,{'input_sha256':key,'status':'complete','result':result});built+=1;results.append(result)
    write_json(ROOT/'corpus_data/validation/stage2_run.json',dict(cache_hits=hits,built=built,pending=pending,total=len(entities)))
    if pending:
        raise SystemExit(f'{len(pending)} entities require review; requests saved under corpus_cache/vision_requests. Existing visual_analysis.json retained.')
    write_json(ROOT/'visual_analysis.json',results)
    print(f'Stage 2: {built} built, {hits} cached; {len(results)} complete.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare-only',action='store_true');args=p.parse_args();build(args.prepare_only)
