from pymongo import MongoClient
import json

import random
import os
import uuid
from datetime import datetime

with open('conf.json', 'r') as f:
    CONFIG = json.load(f)

class Database:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"), maxPoolSize=20)
        self.users = self.client['userdata']
        self.pyqs = self.client['pyqs']
        self.tests = self.client['tests']

    def get_user(self, key, value):
        return self.users['users'].find_one({key: value})
    
    def add_user(self, email):
        user = {
            "_id": str(uuid.uuid4()),
            "email": email,
            "username": email.split("@")[0] + str(random.randint(10000, 99999))
        }
        self.users['users'].insert_one(user)
        return user

    def update_user(self, _id, **kwargs):
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if update_data:
            self.users['users'].update_one({"_id": _id}, {"$set": update_data})

        return self.users['users'].find_one({"_id": _id})

    def delete_user(self, _id):
        self.users['users'].delete_one({"_id": _id})

    def get_exams(self):
        return list(self.pyqs['exams'].find({}, {'_id': 1, 'name': 1}))
    
    def get_subjects_by_exam(self, exam_id, full=False):
        if full:
            return list(self.pyqs['subjects'].find({'exam': exam_id}))
        return list(self.pyqs['subjects'].find({'exam': exam_id}, {'_id': 1, 'name': 1}))
    
    def get_pyqs_by_exam(self, exam_id):
        return list(self.pyqs['papers'].find({'exam': exam_id}))
    
    def generate_test(self, exam_id, subjects, num, ratio):
        test = {}

        subjects = {k: v for k, v in subjects.items() if v != ['']}

        subject_count = len(subjects)
        ques_per_subject = -(-num // subject_count)

        all_chapters_subjects = [s for s, c in subjects.items() if c == ['all']]
        if all_chapters_subjects:
            subject_docs = self.pyqs['subjects'].find({'_id': {'$in': all_chapters_subjects}}, {'_id': 1, 'chapters': 1})
            chapters_map = {doc['_id']: [c[0] for c in doc['chapters']] for doc in subject_docs}
            for s in all_chapters_subjects:
                subjects[s] = chapters_map[s]

        for subject, chapters in subjects.items():
            test[subject] = []

            agg_result = list(self.pyqs['questions'].aggregate([
                {
                    '$match': {
                        'exam': exam_id,
                        'subject': subject,
                        'chapter': {'$in': chapters}
                    }
                },
                {
                    '$facet': {
                        'mcqs': [
                            {'$match': {'type': 'singleCorrect'}},
                            {'$project': {'_id': 1}},
                            {'$sample': {'size': int(ques_per_subject * ratio)}}
                        ],
                        'numericals': [
                            {'$match': {'type': 'numerical'}},
                            {'$project': {'_id': 1}},
                            {'$sample': {'size': ques_per_subject - int(ques_per_subject * ratio)}}
                        ]
                    }
                }
            ]))[0]

            mcq_ids = [q['_id'] for q in agg_result['mcqs']]
            numerical_ids = [q['_id'] for q in agg_result['numericals']]

            test[subject].extend(mcq_ids + numerical_ids)

        return test
    

    def add_test(self, user_id, metadata, questions):
        test_id = str(uuid.uuid4())

        test_data = {
            "_id": test_id,
            "created_by": user_id,
            "created_at": datetime.now(),
            "title": metadata['title'],
            "description": metadata['description'],
            "exam": metadata['exam'],
            "duration": metadata['duration'],
            "mode": metadata['mode'],
            "subjects": metadata['subjects'],
            "questions": questions,
            "attempts": []
        }

        self.tests['tests'].insert_one(test_data)

        self.users['users'].update_one({"_id": user_id}, {
            "$push": {
                "testIds": test_id,
            }
        })

        return test_id
    
    def add_pyq_test(self, user_id, metadata, paper_id):
        test_id = str(uuid.uuid4())

        test_data = {
            "_id": test_id,
            "created_by": user_id,
            "created_at": datetime.now(),
            "title": metadata['title'],
            "exam": metadata['exam'],
            "duration": metadata['duration'],
            "mode": metadata['mode'],
            "paper_id": paper_id,
            "attempts": []
        }

        self.tests['tests'].insert_one(test_data)

        self.users['users'].update_one({"_id": user_id}, {
            "$push": {
                "testIds": test_id,
            }
        })

        self.add_activity(user_id, "test_created", {
            "test_id": test_id,
            "title": metadata['title'],
            "exam": metadata['exam']
        })

        return test_id
    
    def add_activity(self, user_id, action, details):
        activity_data = {
            "action": action,
            "details": details,
            "timestamp": datetime.now()
        }
        self.users['activities'].update_one(
            {"_id": user_id},
            {"$push": {"activities": activity_data}},
            upsert=True
        )

    def get_activities(self, user_id):
        user = self.users['activities'].find_one({"_id": user_id})
        if user:
            activities = user.get('activities', [])
            return sorted(activities, key=lambda x: x.get('timestamp'), reverse=True)
        return []
    
    def get_tests_by_user(self, user_id):
        tests = list(self.tests['tests'].find(
            {"created_by": user_id},
            {"_id": 1, "title": 1, "exam": 1, "created_at": 1, "attempts": 1, "mode": 1, "questions": 1, "paper_id": 1}
        ))

        if not tests:
            return []

        all_attempt_ids = [aid for test in tests for aid in test.get('attempts', [])]
        
        attempt_docs = list(self.tests['attempts'].find(
            {"_id": {"$in": all_attempt_ids}},
            {"_id": 1, "score": 1, "submitted_at": 1}
        ).sort("submitted_at", -1))
        attempt_lookup = {}
        for a in attempt_docs:
            attempt_lookup.setdefault(a['_id'], a)

        # Gather all paper_ids for "previous" mode tests
        paper_ids = [test['paper_id'] for test in tests if test['mode'] == 'previous' and 'paper_id' in test]
        paper_lookup = {}
        if paper_ids:
            paper_docs = self.pyqs['papers'].find(
                {"_id": {"$in": paper_ids}},
                {"_id": 1, "questions": 1}
            )
            paper_lookup = {paper['_id']: paper for paper in paper_docs}

        for test in tests:
            # Attach sorted attempts
            test_attempts = [attempt_lookup[aid] for aid in test.get('attempts', []) if aid in attempt_lookup]
            test['attempts'] = test_attempts

            # Get marking scheme
            exam_config = CONFIG.get(test['exam'], {})
            marking_scheme = exam_config.get('marking_scheme', {})

            # Calculate max marks
            max_marks = 0
            if test['mode'] == 'generate':
                total_questions = sum(len(questions) for questions in test['questions'].values())
            elif test['mode'] == 'previous':
                paper = paper_lookup.get(test.get('paper_id'))
                total_questions = len(paper.get('questions', [])) if paper else 0
            else:
                total_questions = 0

            correct_mark = marking_scheme.get('correct', 1)
            if isinstance(correct_mark, dict):
                correct_mark = correct_mark.get('category_1', 1)

            max_marks = total_questions * correct_mark
            test['max_marks'] = max_marks

        return tests
    
    def get_test_attempts(self, test_id):
        return list(self.tests['attempts'].find({"test_id": test_id}))

    def get_test(self, test_id):
        return self.tests['tests'].find_one({"_id": test_id})
    
    def get_subject(self, subject_id):
        return self.pyqs['subjects'].find_one({"_id": subject_id}, {"_id": 1, "name": 1, "exam": 1, "chapters": 1})
    
    def get_questions_by_ids(self, question_ids, full_data=False):
        questions = list(self.pyqs['questions'].find({"_id": {"$in": question_ids}}))
        if not full_data:
            return questions
        
        exam_ids = {q['exam'] for q in questions}
        subject_ids = {q['subject'] for q in questions}
        chapter_ids = {q['chapter'] for q in questions}
        paper_ids = {q['paper_id'] for q in questions if 'paper_id' in q}
        

        exams = self.pyqs['exams'].find({"_id": {"$in": list(exam_ids)}}, {"_id": 1, "name": 1})
        subjects = self.pyqs['subjects'].find({"_id": {"$in": list(subject_ids)}}, {"_id": 1, "name": 1})
        chapter = self.pyqs['chapters'].find({"_id": {"$in": list(chapter_ids)}}, {"_id": 1, "name": 1})
        papers = self.pyqs['papers'].find({"_id": {"$in": list(paper_ids)}}, {"_id": 1, "name": 1})

        exam_lookup = {doc['_id']: doc['name'] for doc in exams}
        subject_lookup = {doc['_id']: doc['name'] for doc in subjects}
        chapter_lookup = {doc['_id']: doc['name'] for doc in chapter}
        paper_lookup = {doc['_id']: doc['name'] for doc in papers}

        for q in questions:
            q['exam_name'] = exam_lookup[q['exam']]
            q['subject_name'] = subject_lookup[q['subject']]
            q['chapter_name'] = chapter_lookup[q['chapter']] if 'chapter' in q else None
            q['paper_name'] = paper_lookup[q['paper_id']] if 'paper_id' in q else None

        return questions
    
    def get_test_optimized(self, test_id):
        """
        Get a test with optimized data loading for the attempt page.
        Only loads necessary data for the test interface.
        """
        test = self.tests['tests'].find_one({"_id": test_id})
        print(test)
        if not test:
            return None
            
        # Prepare test data for the template
        test_data = {
            '_id': test['_id'],
            'title': test['title'],
            'duration': test['duration'],
            'subjects': []
        }
        
        if test.get('mode') == 'generate':
            # Get all required subject IDs
            subject_ids = list(test.get('subjects', {}).keys())
            
            # One bulk query for all subjects
            subjects_data = {}
            if subject_ids:
                bulk_subjects = list(self.pyqs['subjects'].find(
                    {'_id': {'$in': subject_ids}}, 
                    {'_id': 1, 'name': 1}
                ))
                for subject in bulk_subjects:
                    subjects_data[subject['_id']] = subject
            
            # Get all question IDs
            question_ids = []
            for subject_id, question_list in test.get('questions', {}).items():
                question_ids.extend(question_list)
                
            # One bulk query for all questions - only fetch required fields
            questions_data = {}
            if question_ids:
                bulk_questions = list(self.pyqs['questions'].find(
                    {'_id': {'$in': question_ids}}, 
                    {
                        '_id': 1, 
                        'question': 1, 
                        'type': 1, 
                        'options': 1, 
                        'subject': 1
                    }
                ))
                for question in bulk_questions:
                    questions_data[question['_id']] = question
            
            # Organize questions by subject
            for subject_id, question_ids in test.get('questions', {}).items():
                if subject_id not in subjects_data:
                    continue
                    
                subject_questions = []
                for qid in question_ids:
                    if qid in questions_data:
                        subject_questions.append(questions_data[qid])
                
                test_data['subjects'].append({
                    'id': subject_id,
                    'name': subjects_data[subject_id]['name'],
                    'questions': subject_questions
                })
                
        elif test.get('mode') == 'previous':
            # Get paper data
            paper = self.pyqs['papers'].find_one({'_id': test.get('paper_id')})
            if not paper:
                return test_data
                
            # Get all question IDs from the paper
            question_ids = paper.get('questions', [])
            
            # One bulk query for all questions - only fetch required fields
            questions = []
            if question_ids:
                questions = list(self.pyqs['questions'].find(
                    {'_id': {'$in': question_ids}}, 
                    {
                        '_id': 1, 
                        'question': 1, 
                        'type': 1, 
                        'options': 1, 
                        'subject': 1
                    }
                ))
            
            # Group questions by subject
            subject_questions = {}
            subject_ids = set()
            
            for q in questions:
                subject_id = q.get('subject')
                if not subject_id:
                    continue
                    
                subject_ids.add(subject_id)
                if subject_id not in subject_questions:
                    subject_questions[subject_id] = []
                    
                subject_questions[subject_id].append(q)
            
            # Get subject names in bulk
            subject_names = {}
            if subject_ids:
                bulk_subjects = list(self.pyqs['subjects'].find(
                    {'_id': {'$in': list(subject_ids)}}, 
                    {'_id': 1, 'name': 1}
                ))
                for subject in bulk_subjects:
                    subject_names[subject['_id']] = subject['name']
            
            # Add subjects to test data
            for subject_id, questions in subject_questions.items():
                test_data['subjects'].append({
                    'id': subject_id,
                    'name': subject_names.get(subject_id, 'Unknown'),
                    'questions': questions
                })
        
        # Add activity for starting test
        self.add_activity(test['created_by'], "test_started", {
            "test_id": test_id,
            "title": test['title']
        })
        
        return test_data

    def process_test_submission(self, test_id, user_id, answers, time_spent, question_timings=None):
        """Process test submission with question timing data"""
        test = self.get_test(test_id)
        if not test:
            return {"error": "Test not found"}

        exam_config = CONFIG.get(test['exam'])
        if not exam_config:
            return {"error": "Invalid exam configuration"}
        
        marking_scheme = exam_config['marking_scheme']
        correct_marks = marking_scheme['correct']
        incorrect_marks = marking_scheme['incorrect']
        negative_marking = marking_scheme['negative_marking']

        if not isinstance(answers, dict):
            return {"error": "Invalid answers format"}

        question_ids = list(answers.keys())
        question_docs = self.get_questions_by_ids(
            question_ids
        )
        questions_lookup = {str(q["_id"]): q for q in question_docs}

        score = 0
        feedback = []

        for q_id, user_answer in answers.items():
            question = questions_lookup.get(str(q_id))
            if not question:
                continue  # Skip unknown questions

            # Determine correct answer
            if question['type'] == 'numerical':
                correct_answer = question.get('correct_value')
            else:
                correct_answer = question.get('correct_option', [None])[0]

            is_correct = user_answer == correct_answer

            # Determine marks
            if isinstance(correct_marks, dict):  # Complex marking (per category)
                category = question.get('category', 'category_1')
                pos_mark = correct_marks.get(category, 1)
                neg_mark = incorrect_marks.get(category, 0)
            else:  # Simple marking
                pos_mark = correct_marks
                neg_mark = incorrect_marks

            marks = pos_mark if is_correct else (neg_mark if negative_marking else 0)
            score += marks

            # Append feedback
            feedback_item = {
                "question_id": q_id,
                "correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "marks": marks,
            }
            # Include timing if available
            if question_timings and q_id in question_timings:
                feedback_item["time_taken"] = int(question_timings[q_id])
            feedback.append(feedback_item)

        # Prepare attempt document
        attempt_id = str(uuid.uuid4())
        attempt_data = {
            "_id": attempt_id,
            "user_id": user_id,
            "test_id": test_id,
            "score": score,
            "total_questions": len(question_ids),
            "time_spent": time_spent,
            "feedback": feedback,
            "submitted_at": datetime.now()
        }

        if question_timings:
            attempt_data["question_timings"] = question_timings

        # Insert attempt and update test document atomically
        self.tests['attempts'].insert_one(attempt_data)
        self.tests['tests'].update_one(
            {"_id": test_id},
            {"$push": {"attempts": attempt_id}}
        )

        return {
            "attempt_id": attempt_id,
            "score": score,
            "total_questions": len(question_ids),
            "feedback": feedback
        }

    def create_bookmark_bucket(self, user_id, bucket_name):
        """Create a new bookmark bucket for the user"""
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data:
            data = {
                "_id": user_id,
                "bookmarks": {}
            }
        
        bucket_id = str(uuid.uuid4())
        
        data['bookmarks'][bucket_id] = {
            "name": bucket_name,
            "questions": []
        }

        self.users['bookmarks'].update_one({"_id": user_id}, {"$set": data}, upsert=True)

        return bucket_id

    def add_bookmark(self, user_id, question_id, bucket='default'):
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data:
            data = {
                "_id": user_id,
                "bookmarks": {
                    "default": {
                        "name": "Default",
                        "questions": []
                    }
                }
            }

        if question_id not in data['bookmarks'][bucket]['questions']:
            data['bookmarks'][bucket]['questions'].append(question_id)

        self.users['bookmarks'].update_one({"_id": user_id}, {"$set": data}, upsert=True)

    def get_bookmarks(self, user_id, bucket='default'):
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data:
            return {}
        if 'bookmarks' not in data:
            data['bookmarks'] = {
                "default": {
                    "name": "Default",
                    "questions": []
                }
            }
        
        return data['bookmarks'].get(bucket, {})
    
    def remove_bookmark(self, user_id, question_id, bucket='default'):
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data or 'bookmarks' not in data:
            return
        
        if bucket in data['bookmarks'] and question_id in data['bookmarks'][bucket]['questions']:
            data['bookmarks'][bucket]['questions'].remove(question_id)
            self.users['bookmarks'].update_one({"_id": user_id}, {"$set": data})

    def check_bookmark(self, user_id, question_id):
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data or 'bookmarks' not in data:
            return (False, None)

        for b_id, bucket in data['bookmarks'].items():
            if question_id in bucket['questions']:
                return (True, b_id)
        
        return (False, None)
    
    def get_user_buckets(self, user_id):
        data = self.users['bookmarks'].find_one({"_id": user_id})
        if not data or 'bookmarks' not in data:
            return {}
        
        return data['bookmarks']
    
    def __del__(self):
        self.client.close()