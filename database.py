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