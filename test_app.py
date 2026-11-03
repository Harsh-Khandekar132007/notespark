import unittest
import os
import json
from app import app
from database import (
    init_db, get_all_study_sets, get_study_set, get_flashcards,
    get_quiz_questions, create_study_set, add_flashcards, add_quiz_questions
)
from pdf_service import export_study_set_to_pdf, clean_extracted_text
from ai_service import generate_study_material

class NoteSparkTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_database_and_seed(self):
        sets = get_all_study_sets()
        self.assertGreaterEqual(len(sets), 1)
        first_set = sets[0]
        self.assertIn('title', first_set)
        
        cards = get_flashcards(first_set['id'])
        self.assertGreaterEqual(len(cards), 1)

        questions = get_quiz_questions(first_set['id'])
        self.assertGreaterEqual(len(questions), 1)

    def test_pages_render(self):
        # 1. Dashboard
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome back', res.data)
        self.assertIn(b'NoteSpark', res.data)

        # 2. New Study Set
        res = self.client.get('/new')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Drag a PDF or TXT file here', res.data)

        # 3. Flashcards
        sets = get_all_study_sets()
        set_id = sets[0]['id']
        res = self.client.get(f'/study/{set_id}/flashcards')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Flip card', res.data)

        # 4. Quiz
        res = self.client.get(f'/study/{set_id}/quiz')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Answer options', res.data)

        # 5. Library
        res = self.client.get('/library')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Library', res.data)

        # 6. Performance
        res = self.client.get('/performance')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Performance Tracking', res.data)

    def test_pdf_export_service(self):
        sets = get_all_study_sets()
        set_id = sets[0]['id']
        study_set = get_study_set(set_id)
        cards = get_flashcards(set_id)
        questions = get_quiz_questions(set_id)

        pdf_path = export_study_set_to_pdf(study_set, cards, questions)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)

        # Also test export endpoint
        res = self.client.get(f'/study/{set_id}/export-pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/pdf')

    def test_fallback_ai_generator(self):
        sample_notes = """
        Cellular Respiration is the process by which organisms combine oxygen with foodstuff molecules.
        Glycolysis is the metabolic pathway that converts glucose into pyruvate.
        The Krebs Cycle takes place in the matrix of the mitochondria.
        ATP Synthase is an enzyme that synthesizes adenosine triphosphate.
        """
        res = generate_study_material(
            raw_text=sample_notes,
            create_flashcards=True,
            create_quiz=True,
            create_summary=True,
            difficulty='Medium',
            topic_focus='Cell Biology',
            question_count=5
        )
        self.assertIn('title', res)
        self.assertIn('summary', res)
        self.assertGreaterEqual(len(res['flashcards']), 1)
        self.assertGreaterEqual(len(res['quiz']), 1)
        self.assertEqual(len(res['quiz'][0]['options']), 4)

    def test_api_generate_and_quiz_flow(self):
        # Generate new set via API
        post_data = {
            'notes': 'Database Indexing is a data structure technique used to quickly locate and access data in a database. B-Trees are self-balancing search trees. Hash indexes provide O(1) lookups.',
            'difficulty': 'Medium',
            'topic_focus': 'Databases',
            'question_count': '5',
            'create_flashcards': '1',
            'create_quiz': '1',
            'create_summary': '1'
        }
        res = self.client.post('/api/generate', data=post_data)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        new_set_id = data['study_set_id']

        # Verify quiz questions
        questions = get_quiz_questions(new_set_id)
        self.assertGreaterEqual(len(questions), 1)

        # Submit quiz
        answers = {str(i): questions[i]['correct_index'] for i in range(len(questions))}
        res_quiz = self.client.post(
            f'/api/quiz/{new_set_id}/submit',
            data=json.dumps({'answers': answers}),
            content_type='application/json'
        )
        self.assertEqual(res_quiz.status_code, 200)
        quiz_res = res_quiz.get_json()
        self.assertTrue(quiz_res['success'])
        self.assertEqual(quiz_res['score_percentage'], 100)
        self.assertEqual(quiz_res['correct_count'], len(questions))

    def test_performance_real_data_tracking(self):
        # 1. Get a set with questions
        sets = get_all_study_sets()
        set_id = sets[0]['id']
        questions = get_quiz_questions(set_id)
        self.assertGreaterEqual(len(questions), 1)

        # 2. Submit a real quiz attempt (scoring 100%)
        answers = {str(i): questions[i]['correct_index'] for i in range(len(questions))}
        res = self.client.post(
            f'/api/quiz/{set_id}/submit',
            data=json.dumps({'answers': answers}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)

        # 3. Check performance page
        perf_res = self.client.get('/performance')
        self.assertEqual(perf_res.status_code, 200)
        self.assertIn(b'LATEST TEST GIVEN', perf_res.data)
        self.assertIn(sets[0]['title'].encode('utf-8'), perf_res.data)
        self.assertIn(b'100%', perf_res.data)

    def test_card_status_update(self):
        sets = get_all_study_sets()
        cards = get_flashcards(sets[0]['id'])
        card_id = cards[0]['id']

        res = self.client.post(
            f'/api/card/{card_id}/status',
            data=json.dumps({'status': 'got_it'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

if __name__ == '__main__':
    unittest.main()
