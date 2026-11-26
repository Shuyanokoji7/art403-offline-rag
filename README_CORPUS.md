# ART403 visual and analytical corpus

Start with the [article index](CORPUS_INDEX.md), [quality report](QUALITY_REPORT.md), or [manifest](manifest.csv). The corpus covers all 269 indexed rows from eight lectures, grouped into 223 entities, with 117 shared feature articles. Every article includes **Slide Context** and ends with an exam distractor and correction under **Distinctions**.

## Deliverables

| File or directory | Contents |
|---|---|
| [entities.json](entities.json) | Classification, duplicate grouping, every original index row, accession numbers and all slide references |
| [visual_analysis.json](visual_analysis.json) | 223 medium-specific analyses, claim-level confidence tiers, complete slide-neighbour context, separate significance dimensions, distractors and image references |
| [feature_glossary.json](feature_glossary.json) | 117 researched features, source scopes, draft flags and entity backlinks |
| [articles/](articles/) | 223 entity articles under module folders and 117 shared notes under `_shared/` |
| [manifest.csv](manifest.csv) | All 340 articles, status, sources, lecture/slide references and exact token counts |
| [retrieval_chunks.jsonl](retrieval_chunks.jsonl) | Section-based text records carrying article, slide, status and evidence-category metadata |
| [slides/](slides/) | All 155 page images, 300 DPI, numbered to match the lecture index |
| [corpus_data/sources.json](corpus_data/sources.json) | 81 source records, retrieval dates, retrieval methods and precise support scopes |
| [corpus_data/validation/](corpus_data/validation/) | Pilot, input-bound review attestation, stage reports and audit results |

This build contains **292 sourced articles and 48 draft articles**: 183 sourced / 40 draft entity articles and 109 sourced / 8 draft shared features. “Sourced” identifies a visual, lecture or external basis. Relevant attribution questions are consolidated under **Attribution Note**; verified catalogue corrections appear under **External Checks**. A draft identification does not make directly visible colours, shapes or arrangements uncertain.

## What the analysis records

The primary content is close reading: spatial organization, motifs and their locations, construction, technique, figure and object relationships, print processes, and the physical arrangement of exhibitions. Political, economic/trade, social, regional-identity, religious/cosmological and visual/aesthetic significance are separate fields where supported. Comparison links explicitly use `parallel`, `complementary`, `derivative`, or `antithetical`; the last is an allowed label, not a category forced into this corpus.

The first visual review was performed interactively in this Codex session. It used slide overviews and selected unresized detail crops, following the original ten-type pilot recorded in [pilot.json](corpus_data/validation/pilot.json). The v2 revision added `decorative_object` and rechecked all three cover images in native-pixel crops before reprocessing the corpus. Saved masters are verified at 300 DPI; the model's internal resampling is not exposed. V2 is an editorial and contextual reprocessing of the reviewed evidence, with fresh inspection of the pilot images.

The [authoring contract](corpus_pipeline/editorial_rules.md) governs past and future entities:

- **Tier 1:** visible form, colour, composition and contents are stated plainly.
- **Tier 2:** lecture-supported interpretations begin with **Course reading:**.
- **Tier 3:** unsupported external facts such as exact maker, origin or date are grouped into one **Attribution Note**. “Not established” appears at most once per article.
- Type briefs are menus. Empty and inapplicable sections are omitted; no stock limitation fills a missing field.
- **Slide Context** gathers every same-slide, same-heading and adjacent-slide entity before analysis, then explains the grouping. Blank index headings continue the previous heading within the module and are explicitly labelled as inherited.
- Standalone ceramic, ivory, glass, lacquer and enamel objects use **decorative_object**. Objects depicted inside paintings retain their role within the painting; a ceramics installation remains an exhibition display.
- **Distinctions** contains one specific plausible wrong exam claim and a direct correction, plus labelled comparisons where applicable.

The corrected cover pilot is available as the [ceramic dish](articles/module-1/uncaptioned-floral-dish-on-the-course-cover.md), [floral fabric](articles/module-1/uncaptioned-floral-garment-detail-on-the-course-cover.md), and [trader with horses](articles/module-1/trader-with-horses-mahanabami-dibba-relief.md). Flowers recur on ceramic and cloth; the stone relief supplies people, horses and trade. Together they make the course's cross-media argument about circulating goods, designs and craft knowledge. The relief is not described as carrying the floral motif.

The [v2 revision record](corpus_data/validation/confidence_v2.json) records the pilot, scope and validation. A [complete cached rerun](corpus_data/validation/resume_test.json) reused all 223 analyses and 340 articles, preserving both the hashes and modification times of 347 checked deliverables.

The unverified reconstructed MCQ DOCX was not used. The eight PDFs and `lecture_paintings.md` supply the local evidence. External research supplements it through specifically scoped museum and scholarly sources.

## Organization and provenance

- An entity recurring across modules has one article in its earliest cited module. Its aliases, headings, notes and slide occurrences remain intact.
- Curatorial display views are treated as display entities. Their many indexed component rows remain individually recorded in **Lecture Evidence**; they are not silently discarded or falsely declared to be the same physical object.
- Supplemental course concepts and themes are explicitly marked in `entities.json`; they do not manufacture additional index rows.
- Raw lecture wording remains under **Lecture Evidence**. Catalogue corrections appear near the beginning under **External Checks**. For example, the lecture’s dates for La Japonaise and Mannen Bridge are retained alongside the supported corrections.
- Feature links can denote a visible motif, process, interpretive context or comparison. They do not imply that every connected object literally contains the feature. A shared source about a comparable object does not verify the identity of every slide object.
- `tags` record explicit index context, not guaranteed manufacturing origin. `period-unspecified` and `region-unspecified` are deliberate when that context is missing.
- `status: draft` is attached to unresolved entity identifications or unresolved feature meanings. A sourced entity may link to a draft feature; that connection retains a visible warning and does not turn the disputed meaning into fact.

## Run or resume

Requirements: Python 3.10+, the Python packages in [requirements.txt](corpus_pipeline/requirements.txt), and Poppler’s `pdftoppm`, `pdfinfo`, and `pdftotext` commands. The current workspace has the tools needed to run the pipeline. The tokenizer package is available in `/tmp/art403-corpus-libs`; scripts use that location as a fallback. For a durable independent environment:

```bash
cd '/home/ag/Amazon ML'
python -m venv .venv-corpus
.venv-corpus/bin/pip install -r corpus_pipeline/requirements.txt
.venv-corpus/bin/python corpus_pipeline/run_all.py
```

Within the current environment:

```bash
python corpus_pipeline/run_all.py
python corpus_pipeline/test_pipeline.py
python corpus_pipeline/search.py 'Cassatt aquatint woodblock' --limit 6
python corpus_pipeline/search.py 'Gandaberunda' --sourced-only
```

The search helper returns matching evidence excerpts. It is an offline lexical baseline. For RAG ingestion, use `retrieval_chunks.jsonl` and preserve its status, source, article, slide and confidence metadata. `course_interpretation` distinguishes lecture readings, `unresolved_external_attribution` marks Tier 3 questions, and `exam_distractor_and_correction` carries `contains_false_exam_claim: true`. Confidence-tier lists describe the whole section even when a section spans several chunks. An evidence category of `raw_lecture_assertion` must not override an `external_verification` correction merely because the raw date matches a query.

Token counts use `cl100k_base`, including the entire Markdown file and frontmatter. The cached vocabulary is included under `corpus_data/tokenizer/`; its hash is checked by tiktoken. Section chunks are split to at most 550 content tokens, plus a short title/section prefix, with no text loss and no mid-character Unicode split. Counts are not a prediction of every possible model’s billing tokenizer.

## Stages and caches

| Script | Responsibility | Cache / output |
|---|---|---|
| `stage1_render.py` | Render changed/missing pages and extract text | PDF hashes, `slides/module-N/render.json` |
| `stage1_entities.py` | Apply reviewed grouping and validate exact row coverage | `entities.json`, row coverage record |
| `stage2_analyze.py` | Gather neighbouring evidence, validate attestation, and assemble confidence-tiered annotations | `corpus_cache/stage2/<id>.json` |
| `stage3_ground.py` | Assemble researched features and entity evidence links | Per-feature and per-entity Stage 3 caches |
| `stage4_articles.py` | Render type-specific articles and cross-links | `corpus_cache/stage4/<id>.json` |
| `stage5_manifest.py` | Exact token counts, manifest and retrieval records | `manifest.csv`, `retrieval_chunks.jsonl` |
| `audit.py` | Coverage, image integrity, complete context graph, confidence labels, distractors, links and token counts | Audit JSON and quality report |

The annotation sources are [corpus_data/reviews/](corpus_data/reviews/); the research sources are [corpus_data/grounding/](corpus_data/grounding/). V2's explicit corrections live in [refinements.py](corpus_data/editorial/refinements.py) and the three-row [pilot.json](corpus_data/revisions/confidence-v2/pilot.json). These overlays take precedence over the original module paragraphs. [slide_arguments.py](corpus_data/editorial/slide_arguments.py) supplies 155 authored slide readings. [distractors.py](corpus_data/editorial/distractors.py) and [feature_distractors.py](corpus_data/editorial/feature_distractors.py) supply concrete exam claims. These are readable authoring data; generated JSON and Markdown are outputs.

Identical inputs reuse the caches. Changed reviews, neighbouring index evidence or images, grouping arguments, distractors and editorial policy invalidate the affected analyses. Changed feature evidence updates linked entities and articles. A missing slide argument or authored distractor/correction stops the build. Missing generated articles can be restored; manual edits trigger an error instead of being overwritten. To retain an edit permanently, back it up outside `articles/`, incorporate it into the corresponding authoring source or override, then regenerate the missing article. Keep the backup for comparison.

## Adding or changing evidence

1. Put lecture/index changes in place, record classification/grouping, and run Stage 1. Add authored slide arguments for new slides and a specific distractor/correction for every new entity. Stage 2 requires both; unreviewed inputs then receive a JSON request under `corpus_cache/vision_requests/` without replacing the last complete `visual_analysis.json`.
2. Inspect the requested images, index rows and all gathered slide/heading neighbours. The request includes neighbours' image references. Use `inspect_slides.py` for overviews or native-pixel crops; text-only concepts and discourses use their text route. Recheck the relevant type pilot if changing the vision setup.
3. Update `corpus_data/reviews/moduleN.py` and any applicable v2 override. State observations plainly, prefix course readings, omit empty sections, and keep external attribution questions separate. Update the slide argument and distractor as needed. Complete this review **before** acknowledging it:

   ```bash
   python corpus_pipeline/seal_reviews.py --acknowledge-completed-review --id ENTITY_SLUG
   ```

   The acknowledgement binds exact image hashes and index rows. It is an operator assertion, not an automatic model call or proof of model attention. `run_all.py` deliberately does not invoke it.

4. Research every newly flagged feature and record the source, retrieval receipt, supported scope and draft status where necessary. Update the files under `corpus_data/grounding/`.
5. Run the remaining stages, `test_pipeline.py`, and the audit. The 20 regression tests cover review safety, caching, neighbour gathering, confidence separation, omitted sections, the new object type, retrieval labels, external-edit preservation and Unicode chunking. The full audit verifies every generated article. Generated artifact files are atomic.

The pipeline provides resumable assembly of a completed, reviewed corpus. A fresh vision or research pass remains an explicit evidence-producing step; there is no hidden paid API dependency or automatic claim of such a pass.
