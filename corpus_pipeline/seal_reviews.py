"""Bind completed human/model reviews to exact inputs; never run as an automatic vision step.

Run only after actually reviewing the requested slides and updating the annotations.
The acknowledgement records an operator assertion, not an independent measurement
of a vision model's attention or internal image resolution.
"""
import argparse
from common import ROOT, digest, read_json, write_json
from review_schema import load_reviews

def seal(ids=None):
    path=ROOT/'corpus_data/validation/review_attestation.json'
    data=read_json(path) if path.exists() else {
        'review_date':'2026-11-22',
        'method':'In-session Codex visual review of slide overviews and selected unresized detail crops; exact model version and internal resampling are not exposed. Text-only review for concept_term and theme_discourse.',
        'pilot':'corpus_data/validation/pilot.json',
        'limitations':['300 DPI describes the rendered masters, not the resolution of embedded photographs.',
                      'Not every object received a native-resolution crop; unresolved details remain unasserted.',
                      'This is a review attestation, not an automated image-model API response.'],
        'entities':{}}
    reviewed={r['id'] for r in load_reviews()}
    entities=read_json(ROOT/'entities.json')
    if ids and set(ids)-reviewed: raise ValueError('Unknown review IDs')
    for entity in entities:
        if ids and entity['id'] not in ids: continue
        if entity['id'] not in reviewed: raise ValueError(entity['id'])
        binding={'references':[{k:r[k] for k in ('module','slide','image','image_sha256')} for r in entity['references']],
                 'source_rows_sha256':digest(entity['source_rows'])}
        data['entities'][entity['id']]={'input_sha256':digest(binding),
            'review_file':f"corpus_data/reviews/module{entity['references'][0]['module']}.py",
            'review_scope':'All associated index rows and cited slide content; small details asserted only when resolved or explicitly captioned.'}
    write_json(path,data)
    print(f"Attested {len(data['entities'])} reviewed entities.")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acknowledge-completed-review',action='store_true',required=True)
    p.add_argument('--id',action='append',dest='ids')
    args=p.parse_args();seal(args.ids)
