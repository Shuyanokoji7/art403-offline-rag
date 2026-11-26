"""Regression tests for expensive-stage safety, resumability and text preservation."""
import contextlib,io,json,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
from common import digest,file_hash,write_json,write_text
import stage2_analyze as stage2
import stage4_articles as stage4
from stage5_manifest import split_text,tokenizer,evidence_metadata
from confidence import clean_sections,attribution_note,load_distractors
from slide_context import gather

class ReviewSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'slide.png').write_bytes(b'fixture image content')
        ref=dict(module=1,slide=1,image='slide.png',image_sha256=file_hash(self.root/'slide.png'))
        self.entity=dict(id='test',name='Test',type='concept_term',references=[ref],source_rows=[],artist_date=[],headings=[],notes=[],accession_numbers=[])
        self.review=dict(id='test',type='concept_term',sections={'Definition':'Specific definition.','Nearest Confusable Terms':'Distinct terms.','Applied To':'Slide one.'},comparisons=[],significance={},distinctions=['Do not conflate the terms.'],uncertainties=[],feature_ids=['f'])
        self.context={'occurrences':[],'peer_entities':[],'input_sha256':'fixture'}
        self.distractor={'claim':'The term names a kind of material rather than the process.','why_wrong':'The definition concerns a process and its relationship to the material.'}
        write_json(self.root/'entities.json',[self.entity])
        self.patches=[patch.object(stage2,'ROOT',self.root),patch.object(stage2,'CACHE',self.root/'cache'),patch.object(stage2,'ATTESTATION',self.root/'proof.json'),patch.object(stage2,'load_reviews',return_value=[self.review]),patch.object(stage2,'gather',side_effect=lambda entities:{'test':copy.deepcopy(self.context)}),patch.object(stage2,'load_distractors',return_value={'test':self.distractor})]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in self.patches:p.stop()
        self.temp.cleanup()

    def attest(self):
        binding={'references':[{k:r[k] for k in ('module','slide','image','image_sha256')} for r in self.entity['references']],'source_rows_sha256':digest(self.entity['source_rows'])}
        write_json(self.root/'proof.json',{'method':'test-only fixture','entities':{'test':{'input_sha256':digest(binding)}}})

    def run_stage(self):
        with contextlib.redirect_stdout(io.StringIO()):stage2.build()

    def test_unreviewed_input_queues_without_destroying_existing_output(self):
        target=self.root/'visual_analysis.json';target.write_text('existing completed result')
        with self.assertRaises(SystemExit):self.run_stage()
        self.assertEqual(target.read_text(),'existing completed result')
        req=json.loads((self.root/'corpus_cache/vision_requests/test.json').read_text())
        self.assertTrue(req['text_only']);self.assertEqual(req['image_inputs'],[])

    def test_identical_review_uses_cache_without_rewriting(self):
        self.attest();self.run_stage();p=self.root/'cache/test.json';before=p.stat().st_mtime_ns
        self.run_stage();self.assertEqual(p.stat().st_mtime_ns,before)
        self.assertEqual(json.loads((self.root/'corpus_data/validation/stage2_run.json').read_text())['cache_hits'],1)

    def test_changed_index_requires_new_review(self):
        self.attest();self.run_stage();before=(self.root/'visual_analysis.json').read_bytes()
        self.entity['source_rows']=[{'notes':'New evidence not reviewed.'}];write_json(self.root/'entities.json',[self.entity])
        with self.assertRaises(SystemExit):self.run_stage()
        self.assertEqual((self.root/'visual_analysis.json').read_bytes(),before)

    def test_changed_image_invalidates_stale_stage1_hash(self):
        self.attest();self.run_stage();(self.root/'slide.png').write_bytes(b'changed image')
        with self.assertRaisesRegex(ValueError,'Stale entities.json'):self.run_stage()

    def test_annotation_change_rebuilds_only_matching_cache(self):
        self.attest();self.run_stage();old=json.loads((self.root/'cache/test.json').read_text())['input_sha256']
        self.review['sections']['Definition']='A corrected definition.';self.run_stage()
        result=json.loads((self.root/'cache/test.json').read_text())
        self.assertNotEqual(old,result['input_sha256']);self.assertEqual(result['result']['sections']['Definition'],'Course reading: A corrected definition.')

    def test_neighbour_context_change_invalidates_analysis_cache(self):
        self.attest();self.run_stage();old=json.loads((self.root/'cache/test.json').read_text())['input_sha256']
        self.context['peer_entities']=[{'id':'new-neighbour','name':'New comparison'}];self.run_stage()
        result=json.loads((self.root/'cache/test.json').read_text())
        self.assertNotEqual(old,result['input_sha256'])
        self.assertEqual(result['result']['slide_context']['peer_entities'],self.context['peer_entities'])

class ConfidenceRulesTests(unittest.TestCase):
    def test_observation_survives_an_untranslated_inscription_clause(self):
        sections,claims,gaps=clean_sections({}, {'Text–Image Relationship':'Dark script follows the upper border, not translated in the lecture.'})
        self.assertEqual(sections,{'Text–Image Relationship':'Dark script follows the upper border.'})
        self.assertEqual(claims[0]['tier'],1)
        self.assertEqual(len(gaps),1)

    def test_empty_fields_are_omitted_and_visible_negatives_preserved(self):
        sections,claims,gaps=clean_sections({}, {'Costume & Ethnic Markers':'No ethnic attribution is established.','Composition':'No sky horizon or shore anchors the view.'})
        # The first clause is legacy filler, not a visual description.
        self.assertNotIn('Costume & Ethnic Markers',sections)
        self.assertEqual(sections['Composition'],'No sky horizon or shore anchors the view.')

    def test_visible_colours_and_course_identification_have_separate_tiers(self):
        sections,claims,_=clean_sections({}, {'Colour & Motifs':'Red flowers fill the white field. The caption identifies kalamkari.'})
        self.assertEqual([c['tier'] for c in claims],[1,2])
        self.assertEqual(sections['Colour & Motifs'],'Red flowers fill the white field.\n\nCourse reading: The caption identifies kalamkari.')

    def test_tier_three_does_not_become_a_null_material_section(self):
        sections,_,gaps=clean_sections({}, {'Dyes & Materials':'Dye chemistry is not identified.'})
        self.assertEqual(sections,{})
        self.assertEqual(attribution_note([],gaps),['specific colourant or surface-material identification'])

    def test_new_entity_needs_an_authored_distractor(self):
        from review_schema import load_reviews
        reviews=load_reviews()+[{'id':'new-unreviewed-example','row_ids':[],'distinctions':['A generic disclaimer.']}]
        with self.assertRaisesRegex(ValueError,'Missing authored distractors: new-unreviewed-example'):
            load_distractors(reviews)

    def test_decorative_object_is_a_separate_route(self):
        from common import TYPES
        from review_schema import TYPE_CODES
        from analysis_schema import FIELDS
        self.assertIn('decorative_object',TYPES)
        self.assertEqual(TYPE_CODES['O'],'decorative_object')
        self.assertNotIn('Costume & Ethnic Markers',FIELDS['decorative_object'])

    def test_retrieval_keeps_attribution_and_false_exam_claims_distinct(self):
        self.assertEqual(evidence_metadata('Attribution Note')['confidence_tiers'],[3])
        self.assertEqual(evidence_metadata('Slide Context')['evidence_category'],'course_interpretation')
        self.assertTrue(evidence_metadata('Distinctions')['contains_false_exam_claim'])
        self.assertFalse(evidence_metadata('Composition')['contains_false_exam_claim'])

class SlideContextTests(unittest.TestCase):
    def setUp(self):
        def entity(ident,page,heading,module=1):
            return dict(id=ident,name=ident,type='decorative_object',references=[dict(module=module,slide=page)],source_rows=[dict(module=module,slide=page,heading=heading,notes=ident)])
        self.entities=[entity('a',1,'Trade'),entity('b',1,'Trade'),entity('c',2,'—'),entity('d',3,'Another heading'),entity('e',4,'Trade'),entity('f',1,'Trade',2)]
        self.arguments={f'1:{p}':'An authored grouping argument.' for p in range(1,5)}
        self.arguments['2:1']='An independent module argument.'

    def test_all_slide_mates_heading_peers_and_adjacent_entities_are_gathered(self):
        contexts=gather(self.entities,self.arguments);a=contexts['a']['occurrences'][0]
        self.assertEqual(a['same_slide_ids'],['b'])
        self.assertEqual(a['same_heading_ids'],['b','c','e'])
        self.assertEqual(a['adjacent_slide_ids'],['c'])
        c=contexts['c']['occurrences'][0]
        self.assertTrue(c['heading_inherited']);self.assertEqual(c['heading_from_slide'],1)
        self.assertEqual(c['adjacent_slide_ids'],['a','b','d'])
        self.assertNotIn('f',[e['id'] for e in contexts['a']['peer_entities']])

    def test_changed_neighbour_evidence_changes_the_context_digest(self):
        before=gather(self.entities,self.arguments)['a']['input_sha256']
        self.entities[1]['source_rows'][0]['notes']='Corrected neighbouring object'
        self.assertNotEqual(before,gather(self.entities,self.arguments)['a']['input_sha256'])

    def test_a_new_slide_needs_an_authored_argument(self):
        del self.arguments['1:2']
        with self.assertRaisesRegex(ValueError,'Missing authored slide argument: M1:2'):
            gather(self.entities,self.arguments)

class ArticleSafetyTests(unittest.TestCase):
    def test_csv_line_endings_do_not_trigger_unchanged_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'manifest.csv';text='slug,status\r\nexample,sourced\r\n'
            write_text(path,text);before=path.stat().st_mtime_ns;write_text(path,text)
            self.assertEqual(before,path.stat().st_mtime_ns)
            self.assertEqual(path.read_bytes(),text.encode())

    def test_external_article_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as td,patch.object(stage4,'ROOT',Path(td)):
            path=Path('articles/test.md');stage4.save_article('test',path,{'id':'test'},'Generated article\n')
            (Path(td)/path).write_text('User edited article\n')
            with self.assertRaisesRegex(ValueError,'external edits'):stage4.save_article('test',path,{'id':'test'},'Regenerated article\n')
            self.assertEqual((Path(td)/path).read_text(),'User edited article\n')

    def test_unchanged_article_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as td,patch.object(stage4,'ROOT',Path(td)):
            path=Path('articles/test.md');stage4.save_article('test',path,{},'Article\n');before=(Path(td)/path).stat().st_mtime_ns
            self.assertTrue(stage4.save_article('test',path,{},'Article\n'))
            self.assertEqual(before,(Path(td)/path).stat().st_mtime_ns)

    def test_unicode_chunking_preserves_every_character(self):
        text=('मूर्ति — کالम 🪷; pigment ≠ colour.\n'*200);enc=tokenizer();pieces=split_text(text,enc,100)
        self.assertEqual(''.join(pieces),text)
        self.assertTrue(all(len(enc.encode(p,disallowed_special=()))<=100 for p in pieces))

if __name__=='__main__':unittest.main()
