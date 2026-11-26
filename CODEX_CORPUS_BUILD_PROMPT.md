# Codex prompt — ART403 visual/analytical corpus build

Paste everything below this line directly to Codex as the task.

---

## Goal

Build a grounded, exam-oriented article corpus from the 8 ART403 lecture
PDFs in this folder, for retrieval-augmented Q&A (MCQ and written-answer
study support). The corpus must capture close visual/formal analysis —
composition, hidden motifs, architectural systems, technique, theoretical
vocabulary, and exhibition display — not just artwork names and dates.
Generic facts (dates, attributions, provenance) are secondary; the primary
value is the kind of close reading a vision-capable model can do by
actually looking at each slide, cross-checked against what the slide text
already says.

Source material:
- 8 PDFs: `ART403_Module 1..8*.pdf`
- `lecture_paintings.md` — an existing per-slide extraction (painting
  name, artist/date, heading, 1-2 line notes) covering all 8 modules.
  Treat this as a starting index, not a ceiling — it under-captures
  visual detail since it was built from slide captions alone.

Do NOT use `Art_History_MCQ_Complete_Context_Guide.docx` as a source of
factual content or answer keys. It is a reconstructed, self-flagged
UNVERIFIED chat transcript about last year's exam ("original images were
not available for reinspection," several answers marked disputed). Its
only value here is already folded into the analysis brief below — it
shaped *how* this pipeline analyzes and writes, not what it asserts as
fact.

Build this as a resumable pipeline (separate scripts per stage, each
cacheable), not one monolithic script — the vision pass in Stage 2 is
expensive and will need re-runs.

---

## Stage 1 — Render and classify

Render every page of every `ART403_Module *.pdf` to a 300 DPI PNG:
`slides/<module>/page_<N>.png`, numbered to match the "Slide #" column
already used in `lecture_paintings.md`.

For every row in `lecture_paintings.md`, classify it into exactly one type,
using the heading, notes, and the rendered image together:

- `painting_manuscript`
- `architecture`
- `sculpture_relief`
- `textile`
- `metalwork`
- `print` (woodblock, etching, lithography)
- `photograph`
- `theme_discourse` — no single object; a thematic/curatorial/historiographic
  argument (e.g. headings like "Museum practice, curation and recent
  exhibitions", "Kochi Muziris Biennale and Reclaiming Global Ties",
  "Why Reclaiming the Ocean... Today?")
- `concept_term` — a theory/technical vocabulary term tested independent
  of one artwork (e.g. Orientalism, Occidentalism, Japonisme,
  Chromolithography, Misregistration, Conceptual authorship)
- `exhibition_display` — a slide about how objects were physically
  arranged/curated in a show or museum, not about one object's own features

Merge duplicate rows referring to the same entity across slides (many
works recur — e.g. the same relief appears on slides 9, 10, 11, 25 of
Module 1) into one entity, keeping every heading/note/slide reference it
appeared under.

Output `entities.json`: one object per unique entity with name, type,
artist/date, all headings and notes seen, all lecture+slide references,
and any museum accession number found in the notes text.

---

## Stage 2 — Medium-specific visual and analytical pass

Route each entity to the matching brief below. Send the rendered slide
image(s) plus the entity's existing `lecture_paintings.md` data as context
to a vision-capable model. Skip image analysis only for `concept_term` and
`theme_discourse` (text/argument-only).

**Before running this at scale: test it on one slide of each type first.**
Confirm the vision model is actually resolving fine detail at 300 DPI and
not silently downsampling — this entire stage is worthless if it can't see
small details, and some APIs downsample large images before the model ever
sees them.

### painting_manuscript
- Composition (registers, spiral/radial movement, symmetry, framing)
- Perspective convention (flattened/Indic multi-viewpoint vs imported
  single-point European perspective)
- Palette & pigment (gold leaf, lapis, anything signaling trade)
- Line/"hand" (brushwork features distinguishing painter or atelier)
- Figural style (costume, pose, gesture, courtly markers)
- Text-image relationship (calligraphy, marginalia, illumination), if a
  manuscript page
- Motifs & hidden details: every secondary element — animals, birds,
  mythical/religious figures (angels, devils, yakshas, nagas), foreign
  objects (vases, ships, firearms, instruments) — each with its exact
  location in the frame

### architecture
- Building type & function
- Plan & spatial organization (axial / courtyard / tiered platform)
- Structural system — explicitly flag trabeated (post-and-lintel, Hindu
  temple convention) vs arcuate (arch/dome, Islamic convention) wherever
  it applies; this contrast is the course's throughline
- Elevation & massing (shikhara/gopuram towers vs domes/minarets)
- Ornament vocabulary (stucco, cusped arches, muqarnas, jali, relief
  bands, arabesque vs figural programs)
- Materials & construction technique
- Syncretism: where Hindu and Islamic vocabularies share one structure
- Paired comparison, if the slide sets this building against another
  (e.g. a Deccan madrasa against a Central Asian one)

### sculpture_relief
- Subject & narrative
- Iconographic attributes (weapons, mounts, regalia)
- Pose & gesture
- Material & technique
- Architectural placement (frieze, pillar, gateway — where on the
  structure it sits)
- Costume/ethnic markers used to identify foreign figures

### textile
- Technique (hand-painted/mordant-dyed kalamkari vs block-print vs
  resist-dye)
- Field & border organization (medallion, repeat pattern, framing border)
- Dyes & materials, and their trade geography
- Function (hanging, garment, ritual, trade commodity)
- Circulation (made-where vs found/collected-where)

### metalwork
- Technique (inlay, engraving, repoussé)
- Form & function
- Decorative vocabulary's cultural origin

### print
- Process (relief vs intaglio, number of blocks/colors, registration)
- Edition/circulation context

### photograph
- Studio vs documentary context, subject, what it's evidence of

### theme_discourse
- The argument the slide is making
- Evidence/artworks it cites
- How it connects to the course's throughline (oceanic networks, cultural
  amalgamation, reclaiming erased/marginalized histories)

### concept_term
- Definition, in the course's own usage
- The nearest confusable term(s) and exactly how this one differs
- Which artworks/slides in the corpus this term is applied to

### exhibition_display
- Physical arrangement — exact spatial placement/juxtaposition; never
  settle for a vague description like "effective curation"
- What that specific arrangement communicates
- Objects/works involved and their origin

### Universal additions — apply to every type except theme_discourse/concept_term
- Patronage (commissioned by/for whom, if known)
- Historical context (dynasty, political moment)
- Cross-cultural contact evidence
- Any comparison the lecture explicitly draws against another work
- **Significance, broken into named separate dimensions** wherever more
  than one applies: political, economic/trade, social (artisan/craft
  recognition), regional-identity, religious/cosmological,
  visual/aesthetic. Do not merge these into one blended sentence — exam
  wrong-answers are typically a near-identical list missing or adding
  exactly one dimension, so each dimension must be separately statable.
- **Subject-matter vs technique/medium-origin**, stated explicitly and
  separately whenever a work uses a technique, material, or print
  technology from one culture while depicting subject matter from
  another (e.g. European print technology depicting regional/South Asian
  subject matter, or a Western artist adopting Japanese print technique).

Output `visual_analysis.json`: one entry per entity, fields depending on
type, plus the slide image reference(s) used.

---

## Stage 3 — Ground the significance of flagged features

Collect every distinct motif, ornament term, structural feature, or
concept flagged in Stage 2 (e.g. "Gandaberunda two-headed bird",
"trabeate vs arcuate construction", "chinoiserie cloud-collar costume",
"muqarnas", "misregistration"). Dedupe across entities.

For each, research its art-historical significance via
Wikipedia/Wikidata/academic sources. If no source is found, mark
`status: draft` and restrict the note to what's visually/textually
evident — invent no meaning, no dates, no attributions.

Output `feature_glossary.json`: one entry per distinct feature, its
grounded significance, and every entity where it appears.

---

## Stage 4 — Write the articles

For each unique entity, write one Markdown file with this frontmatter:

```yaml
---
id: <slug>
title: <name>
type: painting_manuscript | architecture | sculpture_relief | textile |
      metalwork | print | photograph | theme_discourse | concept_term |
      exhibition_display
tags: [<period>, <region>, <medium>]
aliases: [<alternate names / lecture heading text>]
status: sourced | draft
source: "ART403 Module <N>, slide <X> (visual analysis) + <web source, if any>"
updated: <today's date>
related: [<slugs sharing a feature, via feature_glossary.json>]
---
```

Sections depend on `type` — use that type's field list from Stage 2 as
the article's headed sections (`## Composition`, `## Structural System`,
`## Motifs & Hidden Details`, `## Technique`, `## Argument`, `## Physical
Arrangement`, etc. — only include sections that type actually has). Every
type except `concept_term`/`theme_discourse` also gets a `## Context`
section (date, patron, dynasty, site, current collection if known) and a
`## Significance` section broken into the named dimensions from Stage 2.

**Every article, every type, ends with a mandatory closing section:**

```
## Distinctions
- The nearest plausible wrong interpretation/paraphrase of this entity's
  significance or meaning, and the specific reason it's incorrect or
  incomplete.
- If this entity is involved in an explicit lecture comparison against
  another work/artist/medium, name the relationship directly
  (antithetical / parallel / complementary / derivative) rather than
  leaving it as an unlabeled `related:` link.
```

Also write one shared article per distinct feature in
`feature_glossary.json` (e.g. "Trabeated vs arcuate construction in the
Deccan", "Gandaberunda motif") listing every entity it connects — this is
the cross-reference layer the lectures build their own comparisons on.

Write each entity's file under `articles/<lecture-slug>/`, mirroring the
source lecture; a shared feature/concept article goes under
`articles/_shared/` since multiple lectures reference it.

---

## Stage 5 — Manifest

Write `manifest.csv`: one row per article with slug, type, status
(sourced/draft), source, which lecture(s)/slide(s) cite it, and token
count. Use this to audit coverage and find which parts of the corpus are
still draft-only before trusting it for exam answers.

---

## Operational notes

- Make Stages 2-4 resumable: cache per-entity results so a re-run only
  processes new or previously-failed entities.
- Do not fabricate specific dates, attributions, measurements, or
  symbolic meanings anywhere. If a claim isn't supported by a rendered
  image, the lecture note, or a fetched source, leave it out.
- Run the one-slide-per-type validation pass before processing all ~270
  slide-rows at full scale.
