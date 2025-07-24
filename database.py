from pymongo import MongoClient
import json
import brotli
from functools import lru_cache

import random
import os
import uuid
from datetime import datetime, timedelta, timezone
import pytz
import time

from utils import ist_now


@lru_cache(maxsize=None)
def load_json_file(path, brotli_compressed=False):
    """
    Load JSON file. If brotli_compressed=True, decompress first.
    Returns a dict keyed by '_id'.
    """
    with open(path, "rb") as f:
        data_bytes = f.read()
        if brotli_compressed:
            data_str = brotli.decompress(data_bytes).decode("utf-8")
        else:
            data_str = data_bytes.decode("utf-8")
        data = json.loads(data_str)
        return {item["_id"]: item for item in data}


class Database:
    def __init__(self):
        _start = time.time()
        self.client = MongoClient(os.getenv("MONGO_URI"), maxPoolSize=20)
        self.users = self.client["userdata"]
        self.activities = self.client["activities"]
        self.sr = self.client["sr_data"]
        self.tests = self.client["tests"]

        self.pyqs = {
            "questions": load_json_file(
                "data/pyqs.questions.json.br", brotli_compressed=True
            ),
            "chapters": load_json_file("data/pyqs.chapters.json"),
            "subjects": load_json_file("data/pyqs.subjects.json"),
            "exams": load_json_file("data/pyqs.exams.json"),
            "papers": load_json_file("data/pyqs.papers.json"),
        }

        with open("data/conf.json", "r") as f:
            self.config = json.load(f)

        with open("data/achievements.json", "r") as f:
            self.achievements = {item["_id"]: item for item in json.load(f)}

        self.weights = {
            "easy": 0.4,
            "med": 0.4,
            "hard": 0.2,
        }

        self.exp_mul = {
            1: 1,
            2: 1.5,
            3: 2,
        }

        print(f"Database initialized in {time.time() - _start:.2f} seconds")

    """
    User management methods
    """

    def get_user(self, key, value):
        return self.users["users"].find_one({key: value})

    def add_user(self, email):
        user = {
            "_id": str(uuid.uuid4()),
            "email": email,
            "username": email.split("@")[0] + str(random.randint(10000, 99999)),
            "created_at": ist_now(),
        }
        self.users["users"].insert_one(user)
        return user

    def update_user(self, _id, **kwargs):
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if update_data:
            self.users["users"].update_one({"_id": _id}, {"$set": update_data})

        return self.users["users"].find_one({"_id": _id})

    def delete_user(self, _id):
        self.users["users"].delete_one({"_id": _id})

    """
    PYQ Management methods
    """

    def get_exams(self):
        return list(self.pyqs["exams"].values())

    def get_subjects(self, exam_id, full=False):
        if full:
            return [i for i in self.pyqs["subjects"].values() if i["exam"] == exam_id]
        return [
            {"_id": i["_id"], "name": i["name"]}
            for i in self.pyqs["subjects"].values()
            if i["exam"] == exam_id
        ]

    def get_chapters(self, subject_id, full=False):
        if full:
            return [
                i for i in self.pyqs["chapters"].values() if i["subject"] == subject_id
            ]
        return [
            {"_id": i["_id"], "name": i["name"]}
            for i in self.pyqs["chapters"].values()
            if i["subject"] == subject_id
        ]

    def get_questions(self, chapter_id, full=False):
        if full:
            return [
                i for i in self.pyqs["questions"].values() if i["chapter"] == chapter_id
            ]
        return [
            {
                "_id": i["_id"],
                "question": i["question"],
                "type": i.get("type", "singleCorrect"),
                "level": i.get("level", "easy"),
                "paper_id": i.get("paper_id"),
            }
            for i in self.pyqs["questions"].values()
            if i["chapter"] == chapter_id
        ]

    def get_pyqs(self, exam_id):
        return [i for i in self.pyqs["papers"].values() if i["exam"] == exam_id]

    def get_exam(self, exam_id):
        return self.pyqs["exams"].get(exam_id, None)

    def get_subject(self, subject_id):
        return self.pyqs["subjects"].get(subject_id, None)

    def get_chapter(self, chapter_id):
        chapter = self.pyqs["chapters"].get(chapter_id, None)
        questions = self.get_questions(chapter_id)
        chapter["questions"] = questions
        return chapter

    def get_question(self, question_id):
        return self.pyqs["questions"].get(question_id, None)

    def get_questions_by_ids(self, question_ids, full_data=False):
        questions = [self.get_question(qid) for qid in question_ids]
        if not full_data:
            return questions

        for q in questions:
            q["exam_name"] = self.get_exam(q["exam"]).get("name")
            q["subject_name"] = self.get_subject(q["subject"]).get("name")
            q["chapter_name"] = self.get_chapter(q["chapter"]).get("name")
            q["paper_name"] = (
                self.pyqs["papers"]
                .get(q.get("paper_id"), {})
                .get("name", "Unknown Paper")
            )

        return questions

    def get_pyq(self, paper_id):
        paper = self.pyqs["papers"].get(paper_id, None)
        questions = [
            {
                "_id": i["_id"],
                "question": i["question"],
                "type": i.get("type", "singleCorrect"),
                "level": i.get("level", "easy"),
                "paper_id": i.get("paper_id"),
            }
            for i in self.pyqs["questions"].values()
            if i["paper_id"] == paper_id
        ]
        paper["questions"] = questions
        return paper

    """
    Test Generation and Management methods
    """

    def generate_test(self, exam_id, subjects, num, ratio=None):
        test = {}

        # Filter out empty subject lists
        subjects = {k: v for k, v in subjects.items() if v != [""]}
        subject_count = len(subjects)
        ques_per_subject = -(-num // subject_count)  # Ceiling division

        # Resolve 'all' chapters
        for subject_id, chapters in subjects.items():
            if chapters == ["all"]:
                subject = self.get_subject(subject_id)
                if subject and "chapters" in subject:
                    subjects[subject_id] = [
                        c[0] for c in subject["chapters"]
                    ]  # use chapter IDs

        # Select questions per subject
        for subject_id, chapters in subjects.items():
            test[subject_id] = []

            # Filter questions matching exam, subject, and chapters
            filtered_questions = [
                q
                for q in self.pyqs["questions"].values()
                if q["exam"] == exam_id
                and q["subject"] == subject_id
                and q.get("chapter") in chapters
            ]

            # Apply both type ratio and difficulty weights
            if isinstance(ratio, (int, float)) and 0 <= ratio <= 1:
                # First separate by question type (MCQ vs numerical)
                mcqs = [
                    q for q in filtered_questions if q.get("type") == "singleCorrect"
                ]
                numericals = [
                    q for q in filtered_questions if q.get("type") == "numerical"
                ]

                # Determine number of each type
                num_mcqs = int(ques_per_subject * ratio)
                num_numericals = ques_per_subject - num_mcqs

                # Apply difficulty weights to MCQs
                if mcqs:
                    # Group MCQs by difficulty level
                    mcqs_by_level = {
                        1: [q for q in mcqs if q.get("level", 2) == 1],  # Easy
                        2: [q for q in mcqs if q.get("level", 2) == 2],  # Medium
                        3: [q for q in mcqs if q.get("level", 2) == 3],  # Hard
                    }

                    # Calculate number of questions to select from each difficulty level
                    mcq_selected = self._select_by_difficulty(mcqs_by_level, num_mcqs)
                    test[subject_id].extend([q["_id"] for q in mcq_selected])

                # Apply difficulty weights to Numericals
                if numericals:
                    # Group numericals by difficulty level
                    numericals_by_level = {
                        1: [q for q in numericals if q.get("level", 2) == 1],  # Easy
                        2: [q for q in numericals if q.get("level", 2) == 2],  # Medium
                        3: [q for q in numericals if q.get("level", 2) == 3],  # Hard
                    }

                    # Calculate number of questions to select from each difficulty level
                    numerical_selected = self._select_by_difficulty(
                        numericals_by_level, num_numericals
                    )
                    test[subject_id].extend([q["_id"] for q in numerical_selected])
            else:
                # Apply only difficulty weights
                questions_by_level = {
                    1: [
                        q for q in filtered_questions if q.get("level", 2) == 1
                    ],  # Easy
                    2: [
                        q for q in filtered_questions if q.get("level", 2) == 2
                    ],  # Medium
                    3: [
                        q for q in filtered_questions if q.get("level", 2) == 3
                    ],  # Hard
                }

                selected_questions = self._select_by_difficulty(
                    questions_by_level, ques_per_subject
                )
                test[subject_id].extend([q["_id"] for q in selected_questions])

        return test

    def _select_by_difficulty(self, questions_by_level, total_count):
        level_to_weight = {1: "easy", 2: "med", 3: "hard"}

        # Calculate target counts
        total_weight = sum(self.weights.values())
        target_counts = {
            lvl: int(total_count * (self.weights[level_to_weight[lvl]] / total_weight))
            for lvl in list(level_to_weight.keys())
        }

        # Adjust last level for remainder
        allocated = sum(target_counts.values())
        if allocated < total_count:
            target_counts[list(level_to_weight.keys())[-1]] += total_count - allocated

        # Select questions per level
        selected_questions = []
        for lvl in list(level_to_weight.keys()):
            pool = questions_by_level[lvl]
            count = min(len(pool), target_counts[lvl])
            if count > 0:
                selected_questions.extend(random.sample(pool, count))

        # Fallback: fill remaining from lower levels
        deficit = total_count - len(selected_questions)
        if deficit > 0:
            for lvl in reversed(list(level_to_weight.keys())):  # Hard → Medium → Easy
                pool = [
                    q for q in questions_by_level[lvl] if q not in selected_questions
                ]
                if pool:
                    take = min(deficit, len(pool))
                    selected_questions.extend(random.sample(pool, take))
                    deficit -= take
                if deficit == 0:
                    break

        return selected_questions

    def add_test(self, user_id, metadata, questions):
        test_id = str(uuid.uuid4())

        test_data = {
            "_id": test_id,
            "created_by": user_id,
            "created_at": ist_now(),
            "title": metadata["title"],
            "description": metadata["description"],
            "exam": metadata["exam"],
            "duration": metadata["duration"],
            "mode": metadata["mode"],
            "subjects": metadata["subjects"],
            "questions": questions,
            "attempts": [],
        }

        self.tests["tests"].insert_one(test_data)

        self.users["users"].update_one(
            {"_id": user_id},
            {
                "$push": {
                    "testIds": test_id,
                }
            },
        )

        return test_id

    def add_pyq_test(self, user_id, metadata, paper_id):
        test_id = str(uuid.uuid4())

        test_data = {
            "_id": test_id,
            "created_by": user_id,
            "created_at": ist_now(),
            "title": metadata["title"],
            "exam": metadata["exam"],
            "duration": metadata["duration"],
            "mode": metadata["mode"],
            "paper_id": paper_id,
            "attempts": [],
        }

        self.tests["tests"].insert_one(test_data)

        self.users["users"].update_one(
            {"_id": user_id},
            {
                "$push": {
                    "testIds": test_id,
                }
            },
        )

        self.add_activity(
            user_id,
            "test_created",
            {"test_id": test_id, "title": metadata["title"], "exam": metadata["exam"]},
        )

        return test_id

    def get_tests_by_user(self, user_id):
        tests = list(
            self.tests["tests"].find(
                {"created_by": user_id},
                {
                    "_id": 1,
                    "title": 1,
                    "exam": 1,
                    "created_at": 1,
                    "attempts": 1,
                    "mode": 1,
                    "questions": 1,
                    "paper_id": 1,
                },
            )
        )

        if not tests:
            return []

        # Bulk fetch all attempts in one call
        all_attempt_ids = [aid for test in tests for aid in test.get("attempts", [])]
        attempt_docs = list(
            self.tests["attempts"]
            .find(
                {"_id": {"$in": all_attempt_ids}},
                {"_id": 1, "score": 1, "submitted_at": 1},
            )
            .sort("submitted_at", -1)
        )
        attempt_lookup = {a["_id"]: a for a in attempt_docs}

        # Bulk fetch papers for 'previous' mode tests
        paper_ids = [
            t["paper_id"] for t in tests if t["mode"] == "previous" and "paper_id" in t
        ]
        paper_lookup = {}
        if paper_ids:
            paper_docs = list(self.pyqs["papers"].values())
            paper_lookup = {p["_id"]: p for p in paper_docs if p["_id"] in paper_ids}

        # Load marking scheme config once
        exam_config_cache = {}
        for test in tests:
            # Attach attempts sorted by submitted_at descending
            test_attempts = [
                attempt_lookup[aid]
                for aid in test.get("attempts", [])
                if aid in attempt_lookup
            ]
            test["attempts"] = sorted(
                test_attempts, key=lambda a: a["submitted_at"], reverse=True
            )

            # Get marking scheme
            exam_id = test["exam"]
            if exam_id not in exam_config_cache:
                exam_config_cache[exam_id] = self.config.get(exam_id, {})
            marking_scheme = exam_config_cache[exam_id].get("marking_scheme", {})
            correct_mark = marking_scheme.get("correct", 1)
            if isinstance(correct_mark, dict):
                correct_mark = correct_mark.get("category_1", 1)

            # Calculate total questions
            if test["mode"] == "generate":
                total_questions = sum(len(qs) for qs in test["questions"].values())
            elif test["mode"] == "previous":
                paper = paper_lookup.get(test.get("paper_id"))
                total_questions = len(paper.get("questions", [])) if paper else 0
            else:
                total_questions = 0

            test["max_marks"] = total_questions * correct_mark

        return tests

    def get_test_attempts(self, test_id):
        return list(self.tests["attempts"].find({"test_id": test_id}))

    def get_test(self, test_id):
        return self.tests["tests"].find_one({"_id": test_id})

    def get_test_optimized(self, test_id):
        test = self.tests["tests"].find_one({"_id": test_id})
        if not test:
            return None

        test_data = {
            "_id": test["_id"],
            "title": test["title"],
            "duration": test["duration"],
            "subjects": [],
        }

        if test.get("mode") == "generate":
            for subject_id, question_ids in test.get("questions", {}).items():
                subject = self.get_subject(subject_id)
                if not subject:
                    continue

                subject_questions = [
                    {
                        "_id": q["_id"],
                        "question": q["question"],
                        "type": q.get("type", "singleCorrect"),
                        "options": q.get("options", []),
                        "subject": q["subject"],
                    }
                    for qid in question_ids
                    if (q := self.get_question(qid))
                ]

                test_data["subjects"].append(
                    {
                        "id": subject_id,
                        "name": subject["name"],
                        "questions": subject_questions,
                    }
                )

        elif test.get("mode") == "previous":
            paper = self.get_pyq(test.get("paper_id"))
            if not paper:
                return test_data

            subject_questions = {}
            for qid in paper.get("questions", []):
                question = self.get_question(qid)
                if not question:
                    continue
                sid = question.get("subject")
                if sid not in subject_questions:
                    subject_questions[sid] = []
                subject_questions[sid].append(
                    {
                        "_id": question["_id"],
                        "question": question["question"],
                        "type": question.get("type", "singleCorrect"),
                        "options": question.get("options", []),
                        "subject": sid,
                    }
                )

            for subject_id, questions in subject_questions.items():
                subject_name = self.get_subject(subject_id).get("name", "Unknown")
                test_data["subjects"].append(
                    {"id": subject_id, "name": subject_name, "questions": questions}
                )

        self.add_activity(
            test["created_by"],
            "test_started",
            {"test_id": test_id, "title": test["title"]},
        )

        return test_data

    def process_test_submission(
        self, test_id, user_id, answers, time_spent, question_timings=None
    ):
        """Process test submission with question timing data"""
        test = self.get_test(test_id)
        if not test:
            return {"error": "Test not found"}

        exam_config = self.config.get(test["exam"])
        if not exam_config:
            return {"error": "Invalid exam configuration"}

        marking_scheme = exam_config["marking_scheme"]
        correct_marks = marking_scheme["correct"]
        incorrect_marks = marking_scheme["incorrect"]
        negative_marking = marking_scheme["negative_marking"]

        if not isinstance(answers, dict):
            return {"error": "Invalid answers format"}

        question_ids = list(answers.keys())
        question_docs = self.get_questions_by_ids(question_ids)
        questions_lookup = {str(q["_id"]): q for q in question_docs}

        score = 0
        feedback = []
        points = 0

        for q_id, user_answer in answers.items():
            question = questions_lookup.get(str(q_id))
            if not question:
                continue  # Skip unknown questions

            # Determine correct answer
            if question["type"] == "numerical":
                correct_answer = question.get("correct_value")
            else:
                correct_answer = question.get("correct_option", [None])[0]

            is_correct = user_answer == correct_answer

            # Determine marks
            if isinstance(correct_marks, dict):  # Complex marking (per category)
                category = question.get("category", "category_1")
                pos_mark = correct_marks.get(category, 1)
                neg_mark = incorrect_marks.get(category, 0)
            else:  # Simple marking
                pos_mark = correct_marks
                neg_mark = incorrect_marks

            marks = pos_mark if is_correct else (neg_mark if negative_marking else 0)
            score += marks
            
            if is_correct:
                points += 10*self.exp_mul[question.get("level", 2)] if question.get("type") == "singleCorrect" else 12*self.exp_mul[question.get("level", 2)]

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
            "submitted_at": ist_now(),
        }

        if question_timings:
            attempt_data["question_timings"] = question_timings

        # Insert attempt and update test document atomically
        self.tests["attempts"].insert_one(attempt_data)
        self.tests["tests"].update_one(
            {"_id": test_id}, {"$push": {"attempts": attempt_id}}
        )
        
        self.add_experience(user_id, points)

        return {
            "attempt_id": attempt_id,
            "score": score,
            "total_questions": len(question_ids),
            "feedback": feedback,
        }

    """
    Activity logging methods
    """

    def add_activity(self, user_id, action, details):
        activity_data = {
            "_id": str(uuid.uuid4()),
            "action": action,
            "details": details,
            "timestamp": ist_now(),
        }
        self.activities[user_id].insert_one(activity_data)
        return activity_data

    def get_activities(self, user_id):
        if user_id in self.activities.list_collection_names():
            activities = list(self.activities[user_id].find({}))
            return sorted(activities, key=lambda x: x.get("timestamp"), reverse=True)

        return []

    def get_paginated_activities(self, user_id, page=1, per_page=10):
        if user_id not in self.activities.list_collection_names():
            return {
                "activities": [],
                "page": 1,
                "per_page": per_page,
                "total_pages": 0,
                "total": 0,
            }

        collection = self.activities[user_id]
        total = collection.count_documents({})
        total_pages = (total + per_page - 1) // per_page  # Ceiling division

        # Clamp page number
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        skip_count = (page - 1) * per_page

        # Fetch only the required page
        cursor = (
            collection.find({})
            .sort("timestamp", -1)  # Sort newest first (optional)
            .skip(skip_count)
            .limit(per_page)
        )

        page_activities = list(cursor)

        return {
            "activities": page_activities,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total": total,
        }

    """
    Bookmark management methods
    """

    def create_bookmark_bucket(self, user_id, bucket_name):
        """Create a new bookmark bucket for the user"""
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data:
            data = {"_id": user_id, "bookmarks": {}}

        bucket_id = str(uuid.uuid4())

        data["bookmarks"][bucket_id] = {"name": bucket_name, "questions": []}

        self.users["bookmarks"].update_one(
            {"_id": user_id}, {"$set": data}, upsert=True
        )

        return bucket_id

    def add_bookmark(self, user_id, question_id, bucket="default"):
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data:
            data = {
                "_id": user_id,
                "bookmarks": {"default": {"name": "Default", "questions": []}},
            }

        if question_id not in data["bookmarks"][bucket]["questions"]:
            data["bookmarks"][bucket]["questions"].append(question_id)

        self.users["bookmarks"].update_one(
            {"_id": user_id}, {"$set": data}, upsert=True
        )

    def get_bookmarks(self, user_id, bucket="default"):
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data:
            return {}
        if "bookmarks" not in data:
            data["bookmarks"] = {"default": {"name": "Default", "questions": []}}

        return data["bookmarks"].get(bucket, {})

    def remove_bookmark(self, user_id, question_id, bucket="default"):
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data or "bookmarks" not in data:
            return

        if (
            bucket in data["bookmarks"]
            and question_id in data["bookmarks"][bucket]["questions"]
        ):
            data["bookmarks"][bucket]["questions"].remove(question_id)
            self.users["bookmarks"].update_one({"_id": user_id}, {"$set": data})

    def check_bookmark(self, user_id, question_id):
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data or "bookmarks" not in data:
            return (False, None)

        for b_id, bucket in data["bookmarks"].items():
            if question_id in bucket["questions"]:
                return (True, b_id)

        return (False, None)

    def get_user_buckets(self, user_id):
        data = self.users["bookmarks"].find_one({"_id": user_id})
        if not data or "bookmarks" not in data:
            return {}

        return data["bookmarks"]

    """
    Achievement management methods
    """

    def unlock_achievement(self, user_id, achievement_id):
        user_data = self.users["achievements"].find_one({"_id": user_id})
        if user_data and achievement_id in user_data.get("unlocked", []):
            return

        self.users["achievements"].update_one(
            {"_id": user_id}, {"$addToSet": {"unlocked": achievement_id}}, upsert=True
        )

        self.add_activity(
            user_id, "achievement_unlocked", {"achievement_id": achievement_id}
        )
        
        points = self.achievements[achievement_id].get("reward_points", 0)
        self.add_experience(user_id, points)

    def get_achievements(self, user_id):
        user_data = self.users["achievements"].find_one({"_id": user_id})
        if not user_data:
            return []

        unlocked_ids = user_data.get("unlocked", [])
        return [
            self.achievements[aid] for aid in unlocked_ids if aid in self.achievements
        ]

    def check_streak_achievements(self, user_id):
        streak_achievements = [
            ("first_step", 1),
            ("consistency_is_key", 7),
            ("marathoner", 30),
            ("streak_beast", 100),
        ]
        streak = 0
        practices = (
            self.activities[user_id]
            .find(
                {"action": "practice_completed", "details.streak_extended": True},
                {"timestamp": 1},
            )
            .sort("timestamp", -1)
        )
        last_day = None

        for practice in practices:
            current_day = practice["timestamp"].date()

            if last_day is None:
                streak = 1
            else:
                delta_days = (last_day - current_day).days

                if delta_days == 1:
                    streak += 1
                elif delta_days > 1:
                    break

            last_day = current_day

            if streak >= 100:
                break

            for achievement_id, days_required in streak_achievements:
                if streak >= days_required:
                    self.unlock_achievement(user_id, achievement_id)

    def check_total_achievements(self, user_id):
        if (
            self.activities[user_id].count_documents(
                {"action": "attempt_question", "details.is_correct": True}
            )
            >= 500
        ):
            self.unlock_achievement(user_id, "problem_crusher")

        if self.activities[user_id].count_documents({"action": "test_completed"}) >= 10:
            self.unlock_achievement(user_id, "exam_ready")

        start_of_day = ist_now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        if (
            self.activities[user_id].count_documents(
                {
                    "action": "test_completed",
                    "timestamp": {"$gte": start_of_day, "$lt": end_of_day},
                }
            )
            >= 5
        ):
            self.unlock_achievement(user_id, "iron_will")

    def check_performance_achievements(
        self,
        user_id,
        percent_correct=None,
        avg_time_per_question=None,
        health_remaining=None,
        q_type=None,
    ):
        if percent_correct == 100.0:
            self.unlock_achievement(user_id, "perfectionist")

        if avg_time_per_question and avg_time_per_question < 30:
            self.unlock_achievement(user_id, "fast_learner")

        if health_remaining and health_remaining <= 5:
            self.unlock_achievement(user_id, "immortal_streak")

        if q_type == "numerical":
            last_activities = (
                self.activities[user_id]
                .find({"action": "attempt_question"})
                .sort("timestamp", -1)
            )
            consecutive_correct = 0
            for activity in last_activities:
                ques = self.get_question(activity["details"]["question_id"])
                if ques and ques.get("type") == "numerical":
                    if activity["details"]["is_correct"] and consecutive_correct < 10:
                        consecutive_correct += 1
                    else:
                        break
            if consecutive_correct >= 10:
                self.unlock_achievement(user_id, "precision_machine")

    def check_time_based_achievements(self, user_id):
        completed_at = ist_now()
        if completed_at.hour < 8:
            self.unlock_achievement(user_id, "early_bird")
        if completed_at.hour >= 22:
            self.unlock_achievement(user_id, "night_owl")

    def check_lucky_guess(self, user_id, question_level, time_taken):
        if question_level == 3 and time_taken <= 5:
            self.unlock_achievement(user_id, "lucky_guess")

    """
    Experience points Methods
    """
    
    def add_experience(self, user_id, points):
        user = self.users["users"].find_one({"_id": user_id})
        if 'points' not in user:
            user['points'] = 0
        user['points'] += points
        self.users["users"].update_one({"_id": user_id}, {"$set": {"points": user['points']}})
        
    def get_experience(self, user_id):
        user = self.users["users"].find_one({"_id": user_id})
        return user.get('points', 0)