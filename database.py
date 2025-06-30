from pymongo import MongoClient

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
        return list(self.tests['tests'].find({"created_by": user_id}, {"_id": 1, "title": 1, "exam": 1, "created_at": 1}))
    
    def get_test(self, test_id):
        return self.tests['tests'].find_one({"_id": test_id})
    
    def get_subject(self, subject_id):
        return self.pyqs['subjects'].find_one({"_id": subject_id}, {"_id": 1, "name": 1, "exam": 1, "chapters": 1})
    
    def get_questions_by_ids(self, question_ids):
        return list(self.pyqs['questions'].find({"_id": {"$in": question_ids}}))
    
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