"""Medium-specific prompts: applicable questions, never mandatory empty sections."""
SCHEMA_VERSION = 'art403-analysis-2.0'
FIELDS = {
 'painting_manuscript':['Composition','Perspective Convention','Palette & Pigment','Line & Hand','Figural Style','Text–Image Relationship','Motifs & Hidden Details'],
 'architecture':['Building Type & Function','Plan & Spatial Organization','Structural System','Elevation & Massing','Ornament Vocabulary','Materials & Construction Technique','Syncretism','Paired Comparison'],
 'sculpture_relief':['Subject & Narrative','Iconographic Attributes','Pose & Gesture','Material & Technique','Architectural Placement','Costume & Ethnic Markers'],
 'decorative_object':['Form & Surface','Composition','Colour & Motifs','Decoration & Technique','Function'],
 'textile':['Technique','Field & Border Organization','Dyes & Materials','Function','Circulation'],
 'metalwork':['Technique','Form & Function','Decorative Vocabulary'],
 'print':['Process','Edition & Circulation'],
 'photograph':['Studio vs Documentary Context','Subject & Evidence'],
 'theme_discourse':['Argument','Evidence & Artworks','Course Throughline'],
 'concept_term':['Definition','Nearest Confusable Terms','Applied To'],
 'exhibition_display':['Physical Arrangement','What the Arrangement Communicates','Objects & Origins'],
}
ALIASES={'Placement':'Architectural Placement','Studio or Documentary Context':'Studio vs Documentary Context','Evidence':'Evidence & Artworks'}
SIGNIFICANCE_DIMENSIONS=['political','economic/trade','social','regional-identity','religious/cosmological','visual/aesthetic']
RELATIONSHIPS={'antithetical','parallel','complementary','derivative'}
