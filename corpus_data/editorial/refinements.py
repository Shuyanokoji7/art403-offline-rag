"""Authored v2 corrections to legacy paragraphs; None omits an inapplicable field.

These preserve the reviewed observations. They are not a new vision pass.
"""
REFINEMENTS = {}

def E(ident, sections, unknown=()):
    REFINEMENTS[ident] = dict(sections=sections, unknown=list(unknown))

E('janamaz-or-hanging-coromandel-kalamkari', {
    'Technique':'Course reading: The caption identifies the cloth as kalamkari.',
    'Function':'Course reading: The paired caption Janamaz/Hanging presents prayer-mat and hanging uses as the lecture’s alternatives.'
}, ['the precise sequence of drawing, printing and resist application'])
E('hampi-and-vijayanagara-mapped-urban-landscape', {'Materials & Construction Technique':None})
E('golconda-coverlet-central-pavilion', {
    'Technique':'Course reading: The caption identifies the coverlet as kalamkari.',
    'Dyes & Materials':'Red, green, dark outlines and a pale ground organize the design.'
}, ['the precise painting and dyeing sequence; specific dyestuffs'])
for ident in ('vijaya-vitthala-warrior-left-relief','vijaya-vitthala-warrior-centre-relief','vijaya-vitthala-warrior-right-relief'):
    E(ident, {'Costume & Ethnic Markers':'Course reading: The collective caption supplies Portuguese, Arab (?) and Indigenous warrior as the three identities in the comparison. The question mark belongs to the lecture’s Arab identification.'})
E('lotus-mahal', {'Structural System':'Repeated cusped arches sit beneath horizontal eaves and stepped roof masses. Course reading: The lecture compares this arcuate vocabulary with temple and palatial tower forms.'})
E('palampore-hanging-rom-934-4-3', {'Dyes & Materials':'Red, blue, brown and yellowish areas are visible. Course reading: The slide identifies the material as cotton.'})
E('uncaptioned-riverside-temple-landscape', {'Studio or Documentary Context':'Site and landscape photographs.'})
E('dutch-warehouse-at-bandar-kota', {'Structural System':None})
E('court-dress-or-dodot-tapi-00-187', {
    'Field & Border Organization':'A large oval patchwork-like field combines small triangular and square patterns within a floral ground. Course reading: The label describes a printed and dyed cotton design.',
    'Function':'Course reading: The label identifies an elite Javanese hip-wrapper. Its additional discussion of ceremonial uses concerns dodots as a garment category.'})
E('siesta-bijapur', {'Palette & Pigment':'Orange-red clothing and green foliage contrast with blue and gold-coloured framing.'})
E('iranian-ghalamzani-lidded-vessel', {'Technique':'Course reading: The slide uses ghalamzani for Iranian engraving on copper and pairs it with the zinc-alloy inlay of the Bidriware basin.'})
E('ibrahim-adil-shah-riding-atash-khan', {'Figural Style':'The ruler is differentiated by position, dress and elaborate elephant trappings. Course reading: The caption names Atash Khan and Chanchal and identifies a European figure within the courtly scene.'}, ['the correspondence between every captioned name and the small figures'])
E('ascetic-riding-a-nag', {'Motifs & Hidden Details':'The rider extends a thin rod toward upper left. The horse droops its head; its vertebrae and ribs project sharply. Course reading: The paired thin bodies connect human and animal frailty within the slide’s ascetic theme.'})
E('bijapur-circular-city-plan', {'Structural System':None})
E('gol-gumbaz', {'Materials & Construction Technique':None})
E('mughal-animal-carpet-possibly-lahore', {'Dyes & Materials':'Red, green, cream and dark blue distinguish animals, foliage and borders.'})
E('silk-animal-carpet-iran', {'Dyes & Materials':'Red, green, cream and dark blue distinguish animals, foliage and borders. Course reading: This Iranian example is captioned silk.'})
E('pigment-preparation-v-a-video-still', {'Studio vs Documentary Context':'A demonstration video still with V&A branding.'}, ['the maker’s identity and specific pigment in the demonstration'])
for ident in ('seated-man-gulshan-composite-folio','three-men-gulshan-composite-folio','reclining-lion-gulshan-composite-folio'):
    E(ident, {'Line & Hand':None}, ['the individual component’s attribution within the assembled album folio'])
E('jahangir-shooting-the-head-of-malik-anbar-on-a-cosmic-globe', {'Figural Style':'Jahangir wears a pink patterned robe, jewelled belt and turban and stands in a firm archery pose. Course reading: The commanding stance supports the portrait’s assertion of imperial authority.'})
E('lithographic-stone-demonstration-video-still', {
    'Studio vs Documentary Context':'Process-demonstration video still.',
    'Composition':'The oblique close-up emphasizes the broad flat surface and the thickness of the stone.'})
E('antiquities-of-india-title-page', {'Text–Image Relationship':'The title resembles an inscription on an architectural object. Course reading: The embedded imprint reads 1799 while the lecture caption gives 1808; the article’s External Checks separates the documented title-sheet date from the lecture’s issue context.'})
E('part-of-the-kanaree-caves-salsette', {'Process':'Course reading: The caption identifies this as an engraving. Shaded tonal passages and colour fill the reproduced plate.'}, ['the exact combination of printing and colouring processes in this impression'])
E('mahavir-chitrasala-studio', {'Process':'A coloured popular print. Course reading: The caption names Chitrasala Studio.'}, ['the exact printing process of this sheet'])
E('kali-and-tara-calcutta-art-studio', {'Process':'Course reading: The lecture attributes the colour print to Calcutta Art Studio. The article’s External Checks documents the sheet as a chromolithograph.'})
E('misregistration-analytical-study-term', {'Applied To':'Course reading: The colour-print examples in Modules 6 and 7 provide contexts for asking how successive printed components align. The term is supplied as an analytical study concept by the corpus brief.'})
E('the-letter-mary-cassatt', {'Process':'Course reading: The lecture pairs Cassatt’s colour print with a Japanese design to compare composition. The article’s External Checks identifies softground etching, drypoint and aquatint as the processes of the finished print.'})
for ident in ('claude-monet-photographic-portrait-in-video','mary-cassatt-photographic-portrait-in-video'):
    E(ident, {'Studio vs Documentary Context':'Course reading: The video labels the sitter and uses the photograph in an account of Japonisme. Tape and film-strip graphics frame the portrait in the video design.'}, ['photographer, photographic date and original photographic process'])
E('geishas-dancing-beato-studio-attribution', {'Studio vs Documentary Context':'The figures pose together among arranged furnishings. Course reading: The lecture presents this as a studio genre scene, captions a hand-coloured albumen print and credits Beato.'})
E('floral-textile-detail-tapi-poster-frame', {'Dyes & Materials':'Red, blue-green and a pale ground form the main colour contrasts.'})
E('sleeping-cupid-above-paper-boats-lampedusa-display', {'What the Arrangement Communicates':'The elevated painting and scattered paper boats connect historical art with a Mediterranean setting. The museum’s trust-and-dialogue title gives this vertical juxtaposition a contemporary social reading.'})
E('vallarpadam-container-terminal-lecture-photograph', {'Studio vs Documentary Context':'Course reading: The lecture uses the terminal photograph as a comparison for The Ship of Tarshish and names Vallarpadam Container Terminal.'}, ['photographic date and named photographer'])
E('elephant-by-the-shore-framed-historical-image', {'Process':'A framed coloured pictorial reproduction.'})
