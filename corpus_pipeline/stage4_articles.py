"""Render entity and shared-feature articles, with per-article safe caches."""
from __future__ import annotations
import os,re,json
from pathlib import Path
from common import ROOT,TEXT_TYPES,digest,file_hash,read_json,write_json,write_text
from confidence import course,clean_sections,attribution_note,interpretation

VERSION='art403-articles-2.0'; UPDATED='2026-11-22'

def article_path(entity):
    return Path('articles')/f"module-{min(r['module'] for r in entity['references'])}"/f"{entity['id']}.md"

def relative(path,target):
    return os.path.relpath(ROOT/target,(ROOT/path).parent).replace(os.sep,'/')

def link(path,target,label):
    return f'[{label.replace(chr(91),chr(40)).replace(chr(93),chr(41))}](<{relative(path,target)}>)'

def yaml_frontmatter(data):
    # JSON strings/arrays are valid YAML scalar/flow values; avoids YAML inference.
    return '---\n'+'\n'.join(f'{k}: {json.dumps(v,ensure_ascii=False)}' for k,v in data.items())+'\n---\n\n'

def citation(source):return f"[{source['title']}]({source['url']})"

def source_label(entity,extra=None):
    refs='; '.join(f"ART403 Module {r['module']}, slide {r['slide']}" for r in entity['references'])
    suffix=' (text/argument analysis)' if entity['type'] in TEXT_TYPES else ' (visual analysis)'
    if extra: suffix+=' + '+'; '.join(s['url'] for s in extra)
    return refs+suffix

def tags_for(entity):
    # Tags describe explicit index context, not necessarily manufacturing origin.
    text=' '.join([entity['name'],*entity['artist_date'],*entity['headings'],*(n['text'] for n in entity['notes'])]).lower()
    periods=sorted(set(re.findall(r'\b(?:\d{1,2}(?:st|nd|rd|th)[ -]century|(?:1[0-9]{3}|20[0-9]{2})(?:[–-]\d{2,4})?)\b',text)))
    places=['hampi','vijayanagara','deccan','bijapur','bidar','golconda','hyderabad','coromandel','lepakshi','agra','mughal','india','indian','japan','japanese','china','chinese','persian','iran','dutch','netherlands','european','calcutta','bengal','kochi','goa','lampedusa','paris','france']
    regions=[p for p in places if re.search(r'\b'+p+r'\b',text)]
    return list(dict.fromkeys([*(periods[:6] or ['period-unspecified']),*(regions or ['region-unspecified']),entity['type']]))

def add_section(lines,title,body):
    if body.strip():lines.extend([f'## {title}','',body,''])

def context_body(a,path,paths):
    context=a['slide_context'];names={e['id']:e['name'] for e in context['peer_entities']}
    out=[]
    if context.get('pilot_summary'):out.extend([context['pilot_summary'],''])
    for item in context['occurrences']:
        out.extend([f"### Module {item['module']}, slide {item['slide']}",''])
        if item['headings']:
            label='; '.join(item['headings'])
            if item['heading_inherited']:label+=f" (continued from slide {item['heading_from_slide']})"
            out.extend(['**Heading context:** '+label,''])
        if not (context.get('pilot_summary') and item['module']==1 and item['slide']==1):out.extend([item['argument'],''])
        for field,label in [('same_slide_ids','Same slide'),('same_heading_ids','Same heading group'),('adjacent_slide_ids','Adjacent slides')]:
            peers=item[field]
            if peers:out.extend(['**'+label+':** '+', '.join(link(path,paths[p],names[p]) for p in peers)+'.',''])
    return '\n'.join(out).rstrip()

def entity_article(e,a,g,features,paths,by_title):
    path=paths[e['id']];direct={s['id']:s for v in g['verifications'] for s in v['sources']}
    aliases=list(dict.fromkeys([r['name'] for r in e['source_rows']]+e['headings']))
    if 'malik-anbar' in e['id']:aliases.append('Jahangir shooting the head of Malik Ambar')
    aliases=[x for x in aliases if x not in ('—',e['name'])]
    meta=dict(id=e['id'],title=e['name'],type=e['type'],tags=tags_for(e),aliases=aliases,
              status=g['status'],source=source_label(e,list(direct.values())),updated=UPDATED,related=g['related'])
    lines=[f"# {e['name']}",'']
    if g['verifications']:
        notes=[]
        for v in g['verifications']:
            notes.append(f"- **{v['kind'].replace('_',' ').capitalize()}:** {v['note']} "+' '.join(citation(s) for s in v['sources']))
        add_section(lines,'External Checks','\n'.join(notes))
    for heading,body in a['sections'].items():add_section(lines,heading,body)
    add_section(lines,'Slide Context',context_body(a,path,paths))
    if e['type'] not in TEXT_TYPES:
        parts=[]
        if e['artist_date']: parts.append('Course reading: **Artist/date as indexed:** '+'; '.join(e['artist_date'])+'.')
        if e['accession_numbers']:parts.append('**Accession numbers recorded in the index:** '+', '.join(x['value'] for x in e['accession_numbers'])+'.')
        add_section(lines,'Context','\n\n'.join(parts))
        sign=[]
        for dimension,body in a['significance'].items():sign.extend([f'### {dimension}','',body,''])
        add_section(lines,'Significance','\n'.join(sign).rstrip())
    gaps=[x for x in a['attribution_gaps'] if x not in g['resolved_uncertainties']]
    if any(v['kind']=='correction' and v['resolves'] for v in g['verifications']):
        gaps=[x for x in gaps if not re.search(r'\bdate\b.*(?:check|verif)|(?:check|verif).*\bdate\b',x,re.I)]
    if gaps:add_section(lines,'Attribution Note','Not established: '+'; '.join(gaps)+'.')
    fnotes=[]
    for ident in a['feature_ids']:
        f=features[ident];label=link(path,paths['feature-'+ident],f['title'])
        if f['status']=='draft':label+=' — **draft interpretation**'
        fnotes.append('- '+label)
    add_section(lines,'Connected Features','\n'.join(fnotes))
    evidence=[]
    for r in e['source_rows']:
        evidence.extend([f"### Module {r['module']}, slide {r['slide']} — {r['row_id']}",'',
            f"**Indexed name:** {r['name']}  ",f"**Artist/date:** {r['artist_date']}  ",f"**Heading:** {r['heading']}",'',r['notes'],''])
    if not evidence:evidence=['Supplemental concept or display unit drawn from the cited slides; it is not an additional row in the original index.','']
    evidence+=['### Source images and text','']
    for r in e['references']:
        evidence.append('- '+link(path,r['image'],f"Module {r['module']}, slide {r['slide']} — 300 DPI PNG")+' · '+link(path,r['text'],'extracted slide text'))
    add_section(lines,'Lecture Evidence','\n'.join(evidence))
    d=a['distractor']
    distinctions=[f"**Exam distractor:** “{d['claim']}”",'',f"**Why it is wrong:** {interpretation(d['why_wrong'])}"]
    for c in a['comparisons']:
        if c['target'] not in by_title:raise ValueError(f'Unknown comparison target {c["target"]}')
        target=by_title[c['target']]
        distinctions.append(f"- **{c['relationship'].capitalize()} — {link(path,paths[target],c['target'])}:** {course(c['reason'])}")
    add_section(lines,'Distinctions','\n'.join(distinctions))
    return meta,yaml_frontmatter(meta)+'\n'.join(lines).rstrip()+'\n'

def feature_article(f,entities,paths):
    ident='feature-'+f['id'];path=paths[ident]
    refs=sorted({(r['module'],r['slide']) for o in f['occurrences'] for r in o['references']})
    source='; '.join(f'ART403 Module {m}, slide {p}' for m,p in refs)
    if f['sources']:source+=' + '+'; '.join(s['url'] for s in f['sources'])
    meta=dict(id=ident,title=f['title'],type='concept_term',tags=['shared-feature',f['id']],aliases=f['aliases'],
              status=f['status'],source=source,updated=UPDATED,related=f['entity_ids'])
    lines=[f"# {f['title']}",'']
    clean,claims,gaps=clean_sections({}, {'Definition':f['grounded_significance']})
    add_section(lines,'Definition and Grounded Significance',clean.get('Definition',''))
    unknown=attribution_note([],gaps)
    if f['status']=='draft' and not unknown:unknown=['the external interpretation beyond the lecture’s stated comparison']
    if unknown:add_section(lines,'Attribution Note','Not established: '+'; '.join(unknown)+'.')
    contexts={}
    for occurrence in f['occurrences']:
        for c in occurrence['slide_context']:
            contexts[c['module'],c['slide']]=c['argument']
    # Identical authored readings can cover several consecutive slides; retain all references.
    grouped={}
    for (m,p),arg in sorted(contexts.items()):grouped.setdefault(arg,[]).append(f'M{m}:{p}')
    add_section(lines,'Slide Context','\n\n'.join('**'+', '.join(refs)+'**\n\n'+arg for arg,refs in grouped.items()))
    add_section(lines,'Applied To','\n'.join('- '+link(path,paths[o['entity_id']],o['title'])+' — '+', '.join(f"M{r['module']}:{r['slide']}" for r in o['references']) for o in f['occurrences']))
    sources=[]
    for s in f['sources']:sources.append(f"- {citation(s)} — {s['support_scope']} Accessed {s['retrieved']}; {s['retrieval_method'].replace('_',' ')}.")
    sources+=['','Research receipts: '+', '.join(link(path,p,Path(p).stem) for p in f['research_logs'])+'.']
    add_section(lines,'Sources','\n'.join(sources))
    d=f['distractor']
    add_section(lines,'Distinctions',f"**Exam distractor:** “{d['claim']}”\n\n**Why it is wrong:** {interpretation(d['why_wrong'])}")
    return meta,yaml_frontmatter(meta)+'\n'.join(lines).rstrip()+'\n'

def save_article(ident,path,meta,text):
    cache=ROOT/'corpus_cache/stage4'/f'{ident}.json';old=read_json(cache) if cache.exists() else {}
    output=ROOT/path;key=digest([VERSION,meta,text])
    if output.exists():
        current=file_hash(output)
        if not old or current!=old.get('output_sha256'):
            raise ValueError(f'Article has external edits; preserve/reconcile before regenerating: {path}')
        if old.get('input_sha256')==key:return True
    write_text(output,text)
    write_json(cache,dict(input_sha256=key,status='complete',output=str(path),output_sha256=file_hash(output),metadata=meta))
    return False

def build():
    entities=read_json(ROOT/'entities.json');analyses={a['id']:a for a in read_json(ROOT/'visual_analysis.json')}
    ground={g['id']:g for g in read_json(ROOT/'corpus_data/entity_grounding.json')};glossary=read_json(ROOT/'feature_glossary.json')
    features={f['id']:f for f in glossary};paths={e['id']:article_path(e) for e in entities}
    paths.update({'feature-'+f['id']:Path('articles/_shared')/f"feature-{f['id']}.md" for f in glossary})
    by_title={e['name']:e['id'] for e in entities};built=0;hits=0;catalogue=[]
    for e in entities:
        meta,text=entity_article(e,analyses[e['id']],ground[e['id']],features,paths,by_title)
        hit=save_article(e['id'],paths[e['id']],meta,text);hits+=int(hit);built+=int(not hit)
        catalogue.append(dict(**meta,path=str(paths[e['id']]),kind='entity',references=e['references'],draft_reasons=ground[e['id']]['unresolved_uncertainties']))
    for f in glossary:
        meta,text=feature_article(f,entities,paths);ident=meta['id']
        hit=save_article(ident,paths[ident],meta,text);hits+=int(hit);built+=int(not hit)
        refs=[{'module':m,'slide':p} for m,p in sorted({(r['module'],r['slide']) for o in f['occurrences'] for r in o['references']})]
        catalogue.append(dict(**meta,path=str(paths[ident]),kind='feature',references=refs,draft_reasons=['External grounding incomplete; see Attribution Note.'] if f['status']=='draft' else []))
    write_json(ROOT/'corpus_data/article_catalogue.json',catalogue)
    write_json(ROOT/'corpus_data/validation/stage4_run.json',dict(built=built,cache_hits=hits,total=len(catalogue)))
    print(f'Stage 4: {built} built, {hits} cached; {len(catalogue)} articles.')

if __name__=='__main__':build()
