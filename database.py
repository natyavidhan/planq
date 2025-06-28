from pymongo import MongoClient

import random
import os
import uuid

class Database:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.users = self.client['userdata']
        self.pyqs = self.client['pyqs']

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

            print(len(mcqs))

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
            print(len(numericals))


        return test
    