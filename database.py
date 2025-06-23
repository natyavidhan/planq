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