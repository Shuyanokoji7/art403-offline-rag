"""Validate corpus coverage, provenance, article contracts, links and token counts."""
from collections import Counter
import csv,json,re,sys
from pathlib import Path
from PIL import Image
import yaml
from common import ROOT,TYPES,TEXT_TYPES,file_hash,index_rows,read_json,write_json,write_text,digest
from analysis_schema import FIELDS,SIGNIFICANCE_DIMENSIONS,RELATIONSHIPS
from stage5_manifest import tokenizer,evidence_metadata
from slide_context import gather
from confidence import GAP

def require(condition,message):
    if not condition:raise ValueError(message)

def build():
    inv=read_json(ROOT/'corpus_data/inventory.json');entities=read_json(ROOT/'entities.json')
    analyses=read_json(ROOT/'visual_analysis.json');features=read_json(ROOT/'feature_glossary.json')
    catalogue=read_json(ROOT/'corpus_data/article_catalogue.json');ground=read_json(ROOT/'corpus_data/entity_grounding.json')
    rows=index_rows();counts=Counter(r['row_id'] for e in entities for r in e['source_rows'])
    require(set(counts)=={r['row_id'] for r in rows} and all(n==1 for n in counts.values()),'Index row coverage')
    require(len({e['id'] for e in entities})==len(entities),'Duplicate entity IDs')
    require({e['id'] for e in entities}=={a['id'] for a in analyses}=={g['id'] for g in ground},'Entity stage mismatch')
    expected_images=set();image_hashes={}
    for module in inv:
        require(file_hash(ROOT/module['pdf'])==module['pdf_sha256'],f"Changed PDF: {module['pdf']}")
        for page in range(1,module['pages']+1):
            path=f"slides/module-{module['module']}/page_{page}.png";expected_images.add(path)
            with Image.open(ROOT/path) as im:
                require(im.size==(module['width'],module['height']),f'Incorrect dimensions: {path}')
                require(all(abs(d-300)<1 for d in im.info.get('dpi',(0,0))),f'Incorrect DPI: {path}')
                im.verify()
            image_hashes[path]=file_hash(ROOT/path)
    require({r['image'] for e in entities for r in e['references']}==expected_images,'Not all rendered slides have an entity/argument reference')
    for e in entities:
        require(e['type'] in TYPES,f"Unknown type {e['id']}")
        for r in e['references']:require(r['image_sha256']==image_hashes[r['image']],f"Stale reference {e['id']}")
        for row in e['source_rows']:
            original=next(r for r in rows if r['row_id']==row['row_id'])
            require(row==original,f"Altered index row {row['row_id']}")
        for accession in e['accession_numbers']:
            require(any(accession['value'] in r['notes'] and accession['row_id']==r['row_id'] for r in e['source_rows']),'Unsupported accession')
    require(any(x['value']=='Z,1.59' for e in entities for x in e['accession_numbers']),'Missing letter/comma accession')
    pilot=read_json(ROOT/'corpus_data/validation/pilot.json')
    require(pilot['reviewed_before_full_scale'] and {x['type'] for x in pilot['checks']}==set(TYPES),'Pilot type coverage')
    for check in pilot['checks']:
        for path in check['images']:require((ROOT/path).exists(),f'Missing pilot image {path}')
    title_ids={e['name']:e['id'] for e in entities};entity_ids=set(title_ids.values());feature_ids={f['id'] for f in features}
    require({f for a in analyses for f in a['feature_ids']}==feature_ids,'Feature coverage')
    gathered=gather(entities)
    for a in analyses:
        ident=a['id']
        require(bool(a['sections']) and all(v.strip() for v in a['sections'].values()),f"Empty analysis {ident}")
        require(a['field_coverage']=={k:('included' if k in a['sections'] else 'omitted') for k in FIELDS[a['type']]},f"Field-menu coverage {ident}")
        require(len(a['distinctions'])==1 and a['distinctions'][0]==a['distractor'],f"Distractor structure {ident}")
        require(len(a['distractor']['claim'])>=25 and len(a['distractor']['why_wrong'])>=25,f"Incomplete distractor {ident}")
        require(set(c['section'] for c in a['claims'])==set(a['sections']),f"Missing claim-level provenance {ident}")
        for c in a['claims']:
            require(c['tier'] in (1,2) and not GAP.search(c['text']),f"Uncertainty left in analysis {ident}: {c['text']}")
            require(c['text'] in a['sections'][c['section']],f"Lost claim {ident}")
        for paragraph in (p for v in a['sections'].values() for p in v.split('\n\n')):
            matching=[c for c in a['claims'] if c['text'] in paragraph]
            if any(c['tier']==2 for c in matching):require(paragraph.startswith('Course reading:'),f"Unlabelled reading {ident}")
        for key,value in gathered[ident].items():require(a['slide_context'][key]==value,f"Incomplete slide context {ident}: {key}")
        require(all(c['argument'].startswith('Course reading:') for c in a['slide_context']['occurrences']),f"Unlabelled slide reading {ident}")
        require(set(a['significance'])<=set(SIGNIFICANCE_DIMENSIONS),'Significance dimension')
        require(bool(a['image_references'])==(a['type'] not in TEXT_TYPES),'Image/text routing')
        require(all(v.startswith('Course reading:') for v in a['significance'].values()),f"Unlabelled significance {ident}")
        for c in a['comparisons']:require(c['target'] in title_ids and c['relationship'] in RELATIONSHIPS,'Comparison target/label')
    for f in features:
        expected={a['id'] for a in analyses if f['id'] in a['feature_ids']}
        require(set(f['entity_ids'])==expected,f"Feature backlinks {f['id']}")
        require(f['status'] in ('sourced','draft') and (f['status']=='draft' or f['sources']),'Grounding status')
        for p in f['research_logs']:require((ROOT/p).exists(),'Missing research receipt')
    paths={a['id']:a['path'] for a in catalogue};meta_by_id={};broken=[];article_files=set()
    for a in catalogue:
        path=ROOT/a['path'];article_files.add(path);text=path.read_text()
        require(text.startswith('---\n'),'Missing frontmatter')
        _,front,body=text.split('---\n',2);meta=yaml.safe_load(front);meta_by_id[meta['id']]=meta
        require(set(['id','title','type','tags','aliases','status','source','updated','related'])<=set(meta),'Frontmatter fields')
        require(meta['id']==a['id'] and meta['status']==a['status'],'Catalogue/article mismatch')
        headings=re.findall(r'^## (.+)$',body,re.M)
        require(headings and headings[-1]=='Distinctions',f"Closing distinction {a['id']}")
        require('Slide Context' in headings,f"Missing Slide Context {a['id']}")
        require(body.count('**Exam distractor:**')==1 and body.count('**Why it is wrong:**')==1,f"Exam distinction {a['id']}")
        require(len(re.findall(r'\bnot established\b',body,re.I))<=1,f"Repeated attribution caveat {a['id']}")
        for heading,section in re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',body,re.M|re.S):
            require(bool(section.strip()),f"Empty article section {a['id']}: {heading}")
            if re.search(r'\bnot established\b',section,re.I):require(heading=='Attribution Note',f"Misplaced attribution caveat {a['id']}")
        require(all(x in paths for x in meta['related']),f"Orphan related slug {a['id']}")
        if a['kind']=='entity':
            analysis=next(x for x in analyses if x['id']==a['id'])
            require(set(analysis['sections'])<=set(headings),f"Lost reviewed section {a['id']}")
            require(all(field not in headings for field,state in analysis['field_coverage'].items() if state=='omitted'),f"Reintroduced empty field {a['id']}")
            for c in analysis['comparisons']:require(f"**{c['relationship'].capitalize()} —" in body,'Unlabelled comparison')
            e=next(e for e in entities if e['id']==a['id'])
            for r in e['source_rows']:require(r['notes'] in body and r['row_id'] in body,'Lost lecture evidence')
        for m in re.finditer(r'\]\(<([^>]+)>\)|\]\(([^)]+)\)',body):
            target=m.group(1) or m.group(2)
            if not target.startswith(('https://','http://','#')):
                if not (path.parent/target.split('#',1)[0]).resolve().exists():broken.append([a['path'],target])
    require(not broken,f'Broken local links: {broken[:8]}')
    cover={r['row_id']:e for e in entities for r in e['source_rows'] if r['row_id'] in ('m1-p01-r01','m1-p01-r02','m1-p01-r03')}
    require(len(cover)==3 and cover['m1-p01-r01']['type']=='decorative_object','Corrected pilot classification')
    cover_ids={e['id'] for e in cover.values()}
    for e in cover.values():
        a=next(x for x in analyses if x['id']==e['id']);c=next(x for x in a['slide_context']['occurrences'] if (x['module'],x['slide'])==(1,1))
        require(cover_ids-{e['id']}<=set(c['same_slide_ids']),'Pilot omitted a slide-mate')
        context=a['slide_context']['pilot_summary'].lower()
        require(all(w in context for w in ('ceramic','textile','stone','trade')),'Pilot cross-media argument')
    dish=next(x for x in analyses if x['id']==cover['m1-p01-r01']['id'])
    require(not {'Costume & Ethnic Markers','Architectural Placement'}&set(dish['sections']),'Inapplicable dish sections')
    require(article_files==set((ROOT/'articles').glob('**/*.md')),'Orphan/missing article file')
    with (ROOT/'manifest.csv').open(newline='') as stream:manifest=list(csv.DictReader(stream))
    require(len(manifest)==len(catalogue) and {r['slug'] for r in manifest}==set(paths),'Manifest coverage')
    enc=tokenizer()
    for row in manifest:
        text=(ROOT/row['path']).read_text()
        require(int(row['token_count'])==len(enc.encode(text,disallowed_special=())),'Token count mismatch')
        require(row['status']==meta_by_id[row['slug']]['status'],'Manifest status')
    chunks=[json.loads(x) for x in (ROOT/'retrieval_chunks.jsonl').read_text().splitlines()]
    require(len({c['id'] for c in chunks})==len(chunks),'Duplicate chunk IDs')
    for c in chunks:
        require(c['article_id'] in paths and c['content_sha256']==digest(c['text']),'Chunk provenance')
        require(c['token_count']==len(enc.encode(c['text'],disallowed_special=())),'Chunk token count')
        analysis=next((a for a in analyses if a['id']==c['article_id']),None)
        require(all(c.get(k)==v for k,v in evidence_metadata(c['section'],analysis).items()),f"Chunk confidence metadata {c['id']}")
    per_module=[]
    for m in inv:
        n=m['module'];per_module.append(dict(module=n,pages=m['pages'],index_rows=sum(r['module']==n for r in rows),
            primary_entity_articles=sum(a['kind']=='entity' and a['path'].startswith(f'articles/module-{n}/') for a in catalogue),
            entity_occurrences=sum(any(r['module']==n for r in e['references']) for e in entities)))
    coverage=Counter(v for a in analyses for v in a['field_coverage'].values())
    report=dict(status='pass',editorial_version='confidence-v2',pages=len(expected_images),input_rows=len(rows),entities=len(entities),features=len(features),articles=len(catalogue),
        types=dict(Counter(e['type'] for e in entities)),entity_statuses=dict(Counter(g['status'] for g in ground)),
        feature_statuses=dict(Counter(f['status'] for f in features)),field_coverage=dict(coverage),
        labelled_comparisons=sum(len(a['comparisons']) for a in analyses),source_records=len(read_json(ROOT/'corpus_data/sources.json')),
        article_tokens=sum(int(r['token_count']) for r in manifest),tokenizer=enc.name,chunks=len(chunks),
        per_module=per_module,broken_local_links=broken,articles_with_slide_context=len(catalogue),
        authored_slide_arguments=len({(c['module'],c['slide']) for a in analyses for c in a['slide_context']['occurrences']}),
        entity_claim_tiers=dict(Counter(c['tier'] for a in analyses for c in a['claims'])),
        exam_distractors=len(catalogue),pilot_revision_passed=True,
        draft_articles=[dict(id=a['id'],path=a['path'],reasons=a['draft_reasons']) for a in catalogue if a['status']=='draft'])
    write_json(ROOT/'corpus_data/validation/audit.json',report)
    lines=['# ART403 corpus quality report','',f"Audit: **PASS** — {len(entities)} entities cover all {len(rows)} index rows exactly once; all {len(expected_images)} slides are rendered at 300 DPI and referenced.",'',
        '| Module | Pages | Index rows | Primary entity articles | Entities cited |','|---|---:|---:|---:|---:|']
    lines += [f"| {m['module']} | {m['pages']} | {m['index_rows']} | {m['primary_entity_articles']} | {m['entity_occurrences']} |" for m in per_module]
    lines += ['',f"There are {len(catalogue)} articles: {len(entities)} entities and {len(features)} shared features. Primary placement uses the earliest cited module; recurrence is preserved in references and the manifest. Shared display rows are retained inside their curatorial display entity, including every original object note.",'',
        '## Evidence and limits','',
        f"Entity articles: {report['entity_statuses'].get('sourced',0)} sourced, {report['entity_statuses'].get('draft',0)} draft. Feature articles: {report['feature_statuses'].get('sourced',0)} sourced, {report['feature_statuses'].get('draft',0)} draft.",'',
        'Sourced means a stated basis in the lecture, inspected image or fetched source. It does **not** mean every date, attribution, patron or provenance has independent catalogue verification. Raw lecture assertions remain labelled. A sourced entity may link to a draft feature; that link does not validate the unresolved meaning.','',
        f"The type briefs are menus: {coverage['included']} applicable fields have substantive analysis; {coverage['omitted']} fields are omitted. Additional entity-specific observations remain included. Visible observations are stated plainly; lecture interpretations carry **Course reading:**. Relevant unresolved external facts appear together in one **Attribution Note**, with ‘not established’ used at most once per article.",'',
        f"All {len(catalogue)} articles include **Slide Context** and one concrete exam distractor with a direct correction. Context gathers every same-slide, same-heading and adjacent-slide entity before analysis. The {report['authored_slide_arguments']} slide arguments explain the comparisons; inherited headings are labelled as continuations. The three-row pilot passed before the full editorial rewrite. Flowers recur on the ceramic dish and textile; the stone relief contributes traders, horses and transport to the cross-media trade/contact argument.",'',
        'Vision review was performed interactively in this Codex session, with slide overviews and selected native-pixel crops. The original ten routes were piloted before bulk review; decorative_object was added and visually piloted for the v2 correction. V2 re-edits that reviewed evidence, rechecks the three cover images and adds contextual readings; it does not claim another full-corpus vision run. The exact model version and its internal resampling are not exposed; 300 DPI is verified for the saved masters. See `corpus_data/validation/pilot.json` and `review_attestation.json`.','',
        f"The audit verifies {report['labelled_comparisons']} labelled comparison links, {report['source_records']} source records and zero broken local links. Comparison labels describe the reviewed relationship; a parallel is not automatically a proven source.",'',
        '## Corrections and qualifications','',
        'External Checks preserve museum-supported corrections alongside the lecture: La Japonaise is dated 1876; Hokusai’s Mannen Bridge is ca.1830–32; Cassatt’s finished Letter combines softground etching, drypoint and aquatint. The Daniell title sheet is documented in 1799, while the lecture’s 1808 issue context remains unresolved. Farrukh Beg’s self-portrait identification remains presumed.','',
        '## Retrieval and reproducibility','',
        f"Manifest tokens: {report['article_tokens']:,}, counted with `{enc.name}` over complete Markdown files including frontmatter. `retrieval_chunks.jsonl` has {len(chunks):,} section-based records carrying article, slide, status and evidence-category metadata. Lexical search is supplied; no embedding service or answer generator has been run.",'',
        'Stages 2–4 cache reviewed inputs and outputs. Changed/unreviewed images queue a review request and stop regeneration; a script never manufactures a fresh visual analysis. Neighbour evidence and authored grouping arguments are part of the analysis cache key. A missing slide argument or distractor stops the build. Article regeneration rejects external edits. Structural checks supplement the editorial review of interpretation and distractor/correction pairs.','',
        '## Draft articles','']
    for a in report['draft_articles']:lines.append(f"- [{a['id']}](<{a['path']}>) — {'; '.join(a['reasons'])}")
    write_text(ROOT/'QUALITY_REPORT.md','\n'.join(lines)+'\n')
    print(f"Audit PASS: {len(expected_images)} pages; {len(rows)} rows; {len(catalogue)} articles; zero broken local links.")

if __name__=='__main__':build()
