from pymongo import MongoClient
import json

import random
import os
import uuid
from datetime import datetime

class Database:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"), maxPoolSize=20, minPoolSize=5, connectTimeoutMS=3000)
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

        ques_per_subject = num // len(subjects.keys()) 

        if num % len(subjects.keys()) != 0:
            ques_per_subject += 1

        for subject in subjects:
            chapters = subjects[subject]
            if len(chapters) == 1 and chapters[0] == 'all':
                chapters = [i[0] for i in self.pyqs['subjects'].find_one({'_id': subject})['chapters']]
            test[subject] = []

            mcqs = list(self.pyqs['questions'].aggregate([
                {
                    '$match': {
                        'exam': exam_id,
                        'subject': subject,
                        'chapter': {'$in': chapters},
                        'type': 'singleCorrect'
                    }
                },
                {
                    '$project': {
                        '_id': 1
                    }
                },
                {
                    '$sample': {'size': int(ques_per_subject * ratio)}
                }
            ]))

            test[subject].extend([i['_id'] for i in mcqs])

            numericals = list(self.pyqs['questions'].aggregate([
                {
                    '$match': {
                        'exam': exam_id,
                        'subject': subject,
                        'chapter': {'$in': chapters},
                        'type': 'numerical'
                    }
                },
                {
                    '$project': {
                        '_id': 1
                    }
                },
                {
                    '$sample': {'size': ques_per_subject - len(mcqs)}
                }
            ]))

            test[subject].extend([i['_id'] for i in numericals])


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
        tests = list(self.tests['tests'].find({"created_by": user_id}, {"_id": 1, "title": 1, "exam": 1, "created_at": 1, "attempts": 1, "mode": 1, "questions": 1}))
        
        # Load marking scheme configuration
        with open('conf.json', 'r') as f:
            config = json.loads(f.read())
        
        for test in tests:
            # Get attempts
            attempts = [i for i in self.tests['attempts'].find({"_id": {"$in": test.get('attempts', [])}}, {"_id": 1, "score": 1, "submitted_at": 1})]
            attempts.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
            test['attempts'] = attempts

            # Calculate max marks based on marking scheme
            exam_config = config.get(test['exam'], {})
            marking_scheme = exam_config.get('marking_scheme', {})
            
            max_marks = 0
            if test['mode'] == 'generate':
                # For custom generated tests
                total_questions = sum(len(questions) for questions in test['questions'].values())
                
                # Handle complex marking schemes (like CAT)
                if isinstance(marking_scheme.get('correct'), dict):
                    # Use category 1 as default if categories not specified
                    max_marks = total_questions * marking_scheme['correct'].get('category_1', 1)
                else:
                    max_marks = total_questions * marking_scheme.get('correct', 1)
            
            elif test['mode'] == 'previous':
                # For previous year papers
                paper = self.pyqs['papers'].find_one({'_id': test.get('paper_id')})
                if paper:
                    total_questions = len(paper.get('questions', []))
                    if isinstance(marking_scheme.get('correct'), dict):
                        max_marks = total_questions * marking_scheme['correct'].get('category_1', 1)
                    else:
                        max_marks = total_questions * marking_scheme.get('correct', 1)
            
            test['max_marks'] = max_marks
            
        return tests
    
    def get_test_attempts(self, test_id):
        return list(self.tests['attempts'].find({"test_id": test_id}))

    def get_test(self, test_id):
        return self.tests['tests'].find_one({"_id": test_id})
    
    def get_subject(self, subject_id):
        return self.pyqs['subjects'].find_one({"_id": subject_id}, {"_id": 1, "name": 1, "exam": 1, "chapters": 1})
    
    def get_questions_by_ids(self, question_ids, full_data=False):
        if not full_data:
            return list(self.pyqs['questions'].find({"_id": {"$in": question_ids}}))
        q = list(self.pyqs['questions'].find({"_id": {"$in": question_ids}}))
        for question in q:
            question['exam_name'] = self.pyqs['exams'].find_one({"_id": question['exam']}, {"name": 1})['name']
            question['subject_name'] = self.pyqs['subjects'].find_one({"_id": question['subject']}, {"name": 1})['name']
            question['paper_name'] = self.pyqs['papers'].find_one({"_id": question.get('paper_id')}, {"name": 1})['name']
        return q
    
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

    # result = db.process_test_submission(test_id, session['user']['id'], answers, time_spent)
    def process_test_submission(self, test_id, user_id, answers, time_spent, question_timings=None):
        """Process test submission with question timing data"""
        test = self.get_test(test_id)
        if not test:
            return {"error": "Test not found"}

        # Load marking scheme from configuration
        with open('conf.json', 'r') as f:
            config = json.loads(f.read())
        
        exam_config = config.get(test['exam'])
        if not exam_config:
            return {"error": "Invalid exam configuration"}
        
        marking_scheme = exam_config['marking_scheme']

        # Validate answers
        if not isinstance(answers, dict):
            return {"error": "Invalid answers format"}

        # Get all questions with their correct answers
        full_questions = {i["_id"]: i for i in self.get_questions_by_ids(list(answers.keys()))}

        # Calculate score and feedback
        score = 0
        feedback = []

        for q_id, user_answer in answers.items():
            question = full_questions.get(str(q_id))
            if not question:
                continue

            if question.get('type') == 'numerical':
                correct_answer = question.get('correct_value')
            else:
                correct_answer = question.get('correct_option')[0]
            is_correct = user_answer == correct_answer
            
            # Calculate marks based on marking scheme
            if marking_scheme['negative_marking']:
                if isinstance(marking_scheme['correct'], dict):
                    # Complex marking scheme (e.g., CAT where different sections have different marks)
                    if is_correct:
                        marks = marking_scheme['correct'].get(question.get('category', 'category_1'), 1)
                    else:
                        marks = marking_scheme['incorrect'].get(question.get('category', 'category_1'), 0)
                else:
                    # Simple marking scheme with fixed marks
                    marks = marking_scheme['correct'] if is_correct else marking_scheme['incorrect']
            else:
                # No negative marking
                marks = marking_scheme['correct'] if is_correct else 0

            score += marks
            feedback.append({
                "question_id": q_id,
                "correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "marks": marks
            })

            # Add question timing to feedback if available
            timing_data = None
            if question_timings and q_id in question_timings:
                timing_data = int(question_timings[q_id]) # Convert to int in case it's a float or string

            feedback[-1]["time_taken"] = timing_data  # Store timing data

        # Save attempt with timing data
        attempt_data = {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "test_id": test_id,
            "score": score,
            "total_questions": len(test['questions']),
            "time_spent": time_spent,
            "feedback": feedback,
            "question_timings": question_timings,  # Store all question timings
            "submitted_at": datetime.now()
        }
        
        self.tests['attempts'].insert_one(attempt_data)

        # Update user's test attempts
        self.tests['tests'].update_one({"_id": test_id}, {
            "$push": {
                "attempts": attempt_data["_id"]
            }
        })

        return {
            "attempt_id": attempt_data["_id"],
            "score": score,
            "total_questions": sum([len(i) for i in test['questions']]),
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