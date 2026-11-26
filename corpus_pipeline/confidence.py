"""Separate observations, course readings and attribution gaps without null filler.

This is editorial normalization of existing reviewed statements, not new vision.
Removed uncertainty clauses remain in structured provenance for inspection.
"""
import re

COURSE_FIELDS={'Definition','Nearest Confusable Terms','Applied To','Argument','Evidence & Artworks','Course Throughline',
 'What the Arrangement Communicates','Objects & Origins','Function','Circulation','Edition & Circulation',
 'Building Type & Function','Syncretism','Paired Comparison','Subject Matter vs Technique Origin','Course Identification'}
COURSE_CUES=re.compile(r'\b(lecture|caption(?:ed)?|label|index|named|attribut(?:ed|ion)|identif(?:ied|ies|ication)|catalogue|museum record|published|publication|collection|commission|devotion|political|religious|cosmolog\w*|symbol\w*|allegor\w*|imperial|lineage|ritual|courtly role|divin(?:e|ity)|suggest\w*|evoke\w*|spiritual|sacred|legitimacy|economic|trade|social|contact|exchange|artisanal knowledge|cultural|interpretation|agency|the slide’s term)\b',re.I)
GAP=re.compile(r'\b(not (?:established|identified|specified|supplied|captioned|translated|transcribed|verified|resolved|inferred|securely catalogued|stated|known|labelled|readable|visible|shown|reconstructed|secure)|unverified|unestablished|unresolved|unreadable|unknown|uncertain|(?:does|do) not (?:\w+\s+){0,2}(?:establish|resolve|specify|state|expose|reveal|date|identify|name|supply|give|assay|justify|provide)|cannot (?:\w+\s+){0,4}(?:determine|determined|identify|identified|read|count|establish|resolve|infer|inferred|reveal|locate|verified|distinguish|derived|measured|certify|separated)|no (?:ethnic attribution|additional|further|legible|specific|exact|pigment species|translation|component-specific attribution|maker or)|not independently|(?:dates?|process|photographer|materials?|metadata).{0,45} (?:are|is) (?:absent|not given)|requires? (?:catalogue |museum |edition-level )?(?:checking|verification))\b',re.I)
ATTRIBUTION=re.compile(r'\b(maker|artist|author|attribut|date|origin|provenance|identity|identification|ethnic|nationality|pigment|dye|fibre|fiber|alloy|material|technique|process|commission|patron|collection|edition|photographer|translation|inscription|script|stone count|block count)\w*',re.I)

def course(text):
    return text if text.startswith('Course reading:') else 'Course reading: '+text

def pieces(text):
    for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z“])',text):
        # Keep the observed half of a sentence when an uncertainty follows it.
        for part in re.split(r';\s+|,\s+but\s+|\s+but\s+(?=are not|no specific|does not)|,\s+(?=not translated|though )',sentence):
            part=part.strip()
            if part:yield part

def clean_sections(review,sections):
    output={};claims=[];gaps=[]
    for heading,body in sections.items():
        kept=[]
        for part in pieces(body):
            if GAP.search(part):
                gaps.append(dict(field=heading,text=part,external_fact=bool(ATTRIBUTION.search(part))))
                continue
            if part.startswith('Course reading:'):
                tier=2;part=part[len('Course reading:'):].strip()
            elif heading in review.get('tier1_fields',[]):tier=1
            elif heading in COURSE_FIELDS or COURSE_CUES.search(part):tier=2
            elif heading in ('Process','Technique') and re.search(r'\b(lithograph|chromolithograph|etching|engraving|woodblock|kalamkari|bidri|albumen|aquatint)\w*',part,re.I):tier=2
            else:tier=1
            if part[-1:] not in '.!?':part+='.'
            part=part[0].upper()+part[1:]
            if kept and kept[-1][0]==tier:kept[-1][1].append(part)
            else:kept.append([tier,[part]])
            claims.append(dict(section=heading,tier=tier,text=part,
                basis='reviewed visual observation' if tier==1 else 'lecture interpretation or caption-supported identification'))
        if kept:output[heading]='\n\n'.join(course(' '.join(texts)) if tier==2 else ' '.join(texts) for tier,texts in kept)
    return output,claims,gaps

def attribution_note(uncertainties,gaps):
    values=list(uncertainties)
    labels=[(r'pigment|dye|chemistry|powdered|metallic paint','specific colourant or surface-material identification'),
            (r'gemstone|assay|alloy|metal or stones','metal composition and gemstone identification'),
            (r'photographer|model maker|ship name','named makers and the original documentation metadata'),
            (r'block count|stone count|matrices|number of (?:blocks|stones|colou?r)','printing-matrix count'),
            (r'edition|impression state','edition or impression state'),
            (r'translat|transcri|script|inscription','reading of the inscription'),
            (r'cast|process|technique|recipe|sequence|method','precise production process'),
            (r'ethnic|nationality|identity|identification','specific personal or cultural identification'),
            (r'origin|provenance|destination|collection','object provenance'),
            (r'\bdate\b','exact dating'),(r'maker|artist|draughtsman|engraver','individual maker credit')]
    for gap in gaps:
        if not gap['external_fact']:continue
        matched=[label for pattern,label in labels if re.search(pattern,gap['text'],re.I)]
        values.extend(matched or [gap['text']])
    # One compact note holds the external gaps; absent visible detail produces no prose.
    unique=[]
    for value in values:
        value=re.sub(r'\bnot established\b','unresolved',value,flags=re.I).strip().rstrip('.')
        if value and value.casefold() not in {x.casefold() for x in unique}:unique.append(value)
    return unique

def interpretation(text):
    """Label interpretive corrections; leave directly observable rebuttals plain."""
    return course(text) if COURSE_CUES.search(text) else text

def load_distractors(reviews):
    import importlib.util
    from common import ROOT
    path=ROOT/'corpus_data/editorial/distractors.py'
    spec=importlib.util.spec_from_file_location('exam_distractors',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    by_id={r['id']:r for r in reviews};by_row={row:r for r in reviews for row in r['row_ids']}
    result={r['id']:r['distractor'] for r in reviews if r.get('distractor')}
    for ref,claim,why in m.DISTRACTORS:
        if ':' in ref:
            module,rest=ref.split(':');page,row=rest.split('.')
            key=f'm{int(module)}-p{int(page):02d}-r{int(row):02d}';review=by_row[key]
        else:review=by_id[ref]
        if review['id'] in result:raise ValueError(f'Duplicate distractor {ref}')
        if not claim.strip() or not why.strip():raise ValueError(f'Missing authored distractor or correction: {ref}')
        result[review['id']]=dict(claim=claim,why_wrong=why,category='entity_specific_exam_claim')
    missing=set(by_id)-set(result)
    if missing:raise ValueError('Missing authored distractors: '+', '.join(sorted(missing)))
    return result
