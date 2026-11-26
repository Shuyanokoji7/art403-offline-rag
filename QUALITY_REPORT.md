# ART403 corpus quality report

Audit: **PASS** — 223 entities cover all 269 index rows exactly once; all 155 slides are rendered at 300 DPI and referenced.

| Module | Pages | Index rows | Primary entity articles | Entities cited |
|---|---:|---:|---:|---:|
| 1 | 25 | 43 | 35 | 35 |
| 2 | 16 | 24 | 21 | 22 |
| 3 | 25 | 40 | 35 | 36 |
| 4 | 10 | 9 | 10 | 10 |
| 5 | 24 | 35 | 34 | 34 |
| 6 | 21 | 30 | 33 | 33 |
| 7 | 14 | 26 | 28 | 29 |
| 8 | 20 | 62 | 27 | 30 |

There are 340 articles: 223 entities and 117 shared features. Primary placement uses the earliest cited module; recurrence is preserved in references and the manifest. Shared display rows are retained inside their curatorial display entity, including every original object note.

## Evidence and limits

Entity articles: 183 sourced, 40 draft. Feature articles: 109 sourced, 8 draft.

Sourced means a stated basis in the lecture, inspected image or fetched source. It does **not** mean every date, attribution, patron or provenance has independent catalogue verification. Raw lecture assertions remain labelled. A sourced entity may link to a draft feature; that link does not validate the unresolved meaning.

The type briefs are menus: 736 applicable fields have substantive analysis; 348 fields are omitted. Additional entity-specific observations remain included. Visible observations are stated plainly; lecture interpretations carry **Course reading:**. Relevant unresolved external facts appear together in one **Attribution Note**, with ‘not established’ used at most once per article.

All 340 articles include **Slide Context** and one concrete exam distractor with a direct correction. Context gathers every same-slide, same-heading and adjacent-slide entity before analysis. The 155 slide arguments explain the comparisons; inherited headings are labelled as continuations. The three-row pilot passed before the full editorial rewrite. Flowers recur on the ceramic dish and textile; the stone relief contributes traders, horses and transport to the cross-media trade/contact argument.

Vision review was performed interactively in this Codex session, with slide overviews and selected native-pixel crops. The original ten routes were piloted before bulk review; decorative_object was added and visually piloted for the v2 correction. V2 re-edits that reviewed evidence, rechecks the three cover images and adds contextual readings; it does not claim another full-corpus vision run. The exact model version and its internal resampling are not exposed; 300 DPI is verified for the saved masters. See `corpus_data/validation/pilot.json` and `review_attestation.json`.

The audit verifies 87 labelled comparison links, 81 source records and zero broken local links. Comparison labels describe the reviewed relationship; a parallel is not automatically a proven source.

## Corrections and qualifications

External Checks preserve museum-supported corrections alongside the lecture: La Japonaise is dated 1876; Hokusai’s Mannen Bridge is ca.1830–32; Cassatt’s finished Letter combines softground etching, drypoint and aquatint. The Daniell title sheet is documented in 1799, while the lecture’s 1808 issue context remains unresolved. Farrukh Beg’s self-portrait identification remains presumed.

## Retrieval and reproducibility

Manifest tokens: 444,413, counted with `cl100k_base` over complete Markdown files including frontmatter. `retrieval_chunks.jsonl` has 2,975 section-based records carrying article, slide, status and evidence-category metadata. Lexical search is supplied; no embedding service or answer generator has been run.

Stages 2–4 cache reviewed inputs and outputs. Changed/unreviewed images queue a review request and stop regeneration; a script never manufactures a fresh visual analysis. Neighbour evidence and authored grouping arguments are part of the analysis cache key. A missing slide argument or distractor stops the build. Article regeneration rejects external edits. Structural checks supplement the editorial review of interpretation and distractor/correction pairs.

## Draft articles

- [uncaptioned-floral-dish-on-the-course-cover](<articles/module-1/uncaptioned-floral-dish-on-the-course-cover.md>) — maker; exact date; place of manufacture; specific ceramic body
- [uncaptioned-floral-garment-detail-on-the-course-cover](<articles/module-1/uncaptioned-floral-garment-detail-on-the-course-cover.md>) — maker; exact date; place of manufacture; fibre and precise decorative technique
- [trader-with-horses-mahanabami-dibba-relief](<articles/module-1/trader-with-horses-mahanabami-dibba-relief.md>) — the trader’s individual identity and the queried Arab identification
- [uncaptioned-riverside-temple-landscape](<articles/module-2/uncaptioned-riverside-temple-landscape.md>) — Site, photographer and date uncaptioned.
- [uncaptioned-miniature-detail-turbaned-man](<articles/module-3/uncaptioned-miniature-detail-turbaned-man.md>) — Artist, sitter, date and original object uncaptioned.
- [european-print-above-the-tambur-portrait-left](<articles/module-3/european-print-above-the-tambur-portrait-left.md>) — Individual print subject, maker and process unresolved.
- [european-print-above-the-tambur-portrait-right](<articles/module-3/european-print-above-the-tambur-portrait-right.md>) — Individual print subject, maker and process unresolved.
- [thin-rider-on-a-marbled-horse-comparison-image](<articles/module-3/thin-rider-on-a-marbled-horse-comparison-image.md>) — Left image has no separate title, maker or date.
- [uncaptioned-domed-complex-possible-ibrahim-rauza](<articles/module-3/uncaptioned-domed-complex-possible-ibrahim-rauza.md>) — Site identification remains provisional.
- [voc-ship-model-video-documentation](<articles/module-4/voc-ship-model-video-documentation.md>) — Specific model identity, maker and original photograph metadata are absent.
- [akbars-church-agra](<articles/module-5/akbars-church-agra.md>) — Chronology of the visible building phases is not established by the slide.
- [crucifixion-durer-attribution-queried](<articles/module-5/crucifixion-durer-attribution-queried.md>) — Caption explicitly queries attribution; precise print catalogue identity unresolved.
- [luna-print-inset-in-the-gulshan-album](<articles/module-5/luna-print-inset-in-the-gulshan-album.md>) — Printmaker, process and precise edition not supplied.
- [seated-man-gulshan-composite-folio](<articles/module-5/seated-man-gulshan-composite-folio.md>) — Individual attribution and date are not assigned by the lecture.
- [three-men-gulshan-composite-folio](<articles/module-5/three-men-gulshan-composite-folio.md>) — Individual attribution and date are not assigned by the lecture.
- [reclining-lion-gulshan-composite-folio](<articles/module-5/reclining-lion-gulshan-composite-folio.md>) — Individual attribution and date are not assigned by the lecture.
- [standing-ruler-drawing-possibly-rembrandt](<articles/module-5/standing-ruler-drawing-possibly-rembrandt.md>) — Artist and exact drawing identity are not captioned on slide 24.
- [saint-sebastian-woodblock-matrix](<articles/module-6/saint-sebastian-woodblock-matrix.md>) — Exact object, maker and date are unspecified.
- [saint-sebastian-woodblock-impression](<articles/module-6/saint-sebastian-woodblock-impression.md>) — Exact object, maker and date are unspecified.
- [lithographic-stone-demonstration-video-still](<articles/module-6/lithographic-stone-demonstration-video-still.md>) — Image identity, maker and demonstration metadata are not provided.
- [antiquities-of-india-title-page](<articles/module-6/antiquities-of-india-title-page.md>) — 1799-looking plate imprint versus 1808 caption requires edition-level verification.
- [jazb-al-qulub-ila-diyar-al-mahbub-lithographed-cover](<articles/module-6/jazb-al-qulub-ila-diyar-al-mahbub-lithographed-cover.md>) — Printer transcription needs catalogue correction.
- [mahavir-chitrasala-studio](<articles/module-6/mahavir-chitrasala-studio.md>) — Exact print process and edition uncaptioned.
- [figure-by-a-tree-and-mountain-ukiyo-e-video-image](<articles/module-7/figure-by-a-tree-and-mountain-ukiyo-e-video-image.md>) — Original work, artist, date and whether the source is painting or print are unresolved.
- [olympia-reproduction-inside-zolas-portrait](<articles/module-7/olympia-reproduction-inside-zolas-portrait.md>) — Separate print metadata and, for unnamed components, catalogue identification need verification.
- [japanese-standing-figure-print-inside-zolas-portrait](<articles/module-7/japanese-standing-figure-print-inside-zolas-portrait.md>) — Separate print metadata and, for unnamed components, catalogue identification need verification.
- [monochrome-group-reproduction-inside-zolas-portrait](<articles/module-7/monochrome-group-reproduction-inside-zolas-portrait.md>) — Separate print metadata and, for unnamed components, catalogue identification need verification.
- [claude-monet-photographic-portrait-in-video](<articles/module-7/claude-monet-photographic-portrait-in-video.md>) — Original photographic metadata uncaptioned.
- [mary-cassatt-photographic-portrait-in-video](<articles/module-7/mary-cassatt-photographic-portrait-in-video.md>) — Original photographic metadata uncaptioned.
- [view-of-tokyo-nineteenth-century-photograph](<articles/module-7/view-of-tokyo-nineteenth-century-photograph.md>) — Exact place, photographer, process and date remain unspecified.
- [floral-textile-detail-tapi-poster-frame](<articles/module-8/floral-textile-detail-tapi-poster-frame.md>) — Specific textile identity, date and technique uncaptioned.
- [interwoven-globe-entrance-banner-arrangement](<articles/module-8/interwoven-globe-entrance-banner-arrangement.md>) — Individual entrance-display objects are not labelled legibly.
- [interwoven-globe-gallery-sightline](<articles/module-8/interwoven-globe-gallery-sightline.md>) — Individual exhibited-object identities and origins remain unverified.
- [asia-in-amsterdam-entrance-and-gallery-arrangements](<articles/module-8/asia-in-amsterdam-entrance-and-gallery-arrangements.md>) — Object-level labels and production origins in the gallery views are not legible.
- [the-cloth-that-changed-the-world-rom-display](<articles/module-8/the-cloth-that-changed-the-world-rom-display.md>) — Individual object metadata unresolved.
- [underwater-ceramics-shipwreck-video-still](<articles/module-8/underwater-ceramics-shipwreck-video-still.md>) — Exact underwater site and objects not captioned.
- [unidentified-reclining-figure-on-a-beach](<articles/module-8/unidentified-reclining-figure-on-a-beach.md>) — Artwork, maker, date, location and intended meaning unidentified.
- [sleeping-cupid-above-paper-boats-lampedusa-display](<articles/module-8/sleeping-cupid-above-paper-boats-lampedusa-display.md>) — Paper-boat creator and full curatorial statement not supplied.
- [seated-figure-with-a-log-l-n-tallur](<articles/module-8/seated-figure-with-a-log-l-n-tallur.md>) — Individual title, date, materials and participation instructions are uncaptioned.
- [elephant-by-the-shore-framed-historical-image](<articles/module-8/elephant-by-the-shore-framed-historical-image.md>) — Original work identity, medium, maker and date unresolved.
- [feature-circular-city](<articles/_shared/feature-circular-city.md>) — External grounding incomplete; see Attribution Note.
- [feature-narasimha-vasantotsava](<articles/_shared/feature-narasimha-vasantotsava.md>) — External grounding incomplete; see Attribution Note.
- [feature-ocean-contemporary](<articles/_shared/feature-ocean-contemporary.md>) — External grounding incomplete; see Attribution Note.
- [feature-orientalism-occidentalism](<articles/_shared/feature-orientalism-occidentalism.md>) — External grounding incomplete; see Attribution Note.
- [feature-poster](<articles/_shared/feature-poster.md>) — External grounding incomplete; see Attribution Note.
- [feature-ramayana](<articles/_shared/feature-ramayana.md>) — External grounding incomplete; see Attribution Note.
- [feature-stucco](<articles/_shared/feature-stucco.md>) — External grounding incomplete; see Attribution Note.
- [feature-yogini-andal](<articles/_shared/feature-yogini-andal.md>) — External grounding incomplete; see Attribution Note.
