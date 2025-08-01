from utils import generate_ch_difficulty, ist_now
from utils.database import Database
import math
import time
from datetime import datetime, timedelta

class SR:
    def __init__(self, db: Database):
        _start = time.time()

        self.db = db

        self.difficulty = generate_ch_difficulty(
            self.db.pyqs["chapters"], self.db.pyqs["questions"]
        )

        self.ch_data = {}

        for ch, diff in self.difficulty.items():
            level = diff["average_level"]
            decay_rate = 1 + 0.1 * (level - 1)
            revision_threshold = round(min(25, max(5, 0.15 * diff["question_count"])))
            ease_factor = 2.5 - (0.3 * (level - 1))
            penalty = 0.1 + 0.05 * (level - 1)
            bonus = 0.05 + 0.03 * (level - 1)

            self.ch_data[ch] = {
                "_id": ch,
                "name": diff["name"],
                "count": diff["question_count"],
                "level": level,
                "dr": decay_rate,
                "rt": revision_threshold,
                "ef": ease_factor,
                "penalty": penalty,
                "bonus": bonus,
            }

        self.meta = {
            "easy": {"avg_time": 60000, "q_amt": 0.4},
            "med": {"avg_time": 180000, "q_amt": 0.4},
            "hard": {"avg_time": 300000, "q_amt": 0.2},
        }

        self.sr_db = self.db.client["sr"]

        print(f"Spaced Repetition Module initialized in {time.time()-_start:.2f} seconds")

    def calculate_quality(self, status, time_taken):
        if (time_taken < 5000 and status == False) or status == None:
            return 0
        if status == False:
            return 1
        else:
            if time_taken < 10000:
                return 3
            else:
                return 2

    def calculate_interval(self, chapter_id, last_interval, ef, quality):
        if quality <= 1.5:
            interval = last_interval * (ef - self.ch_data[chapter_id]["penalty"])
        elif quality >= 2.5:
            interval = last_interval * (ef + self.ch_data[chapter_id]["bonus"])
        else:
            interval = last_interval * ef
        return max(1, round(interval))

    def calculate_retention(self, last_revision, interval, chapter_id):
        retention = math.exp(
            (-self.ch_data[chapter_id]["dr"] * last_revision) / interval
        )
        return retention

    def calculate_ease_factor(self, ef_old, quality):
        ef_new = ef_old + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02))
        return max(1.3, min(2.5, ef_new))
    
    def calculate_delta(self, last_revision: datetime, interval):
        delta = ((last_revision + timedelta(days=interval)) - ist_now()).days
        return delta

    def update_progress(self, user_id, chapter_id, practice_data):
        if self.ch_data[chapter_id]["rt"] > len(set(i['details']['question_id'] for i in practice_data)):
            print("Not enough questions attempted for chapter:", chapter_id)
            return
        
        total = sum(
            self.calculate_quality(q['details']["is_correct"], q['details']["time_taken"])
            for q in practice_data
        )
        quality = total / len(practice_data)

        data = self.sr_db[user_id].find_one({"_id": chapter_id})
        now = ist_now()
        if not data:
            default = self.ch_data[chapter_id]
            data = {
                "_id": chapter_id,
                "ef": self.calculate_ease_factor(default["ef"], quality),
                "last_revision": now,
                "interval": 6,
                "attempted": [],
                "delta": 0
            }
        else:
            delta = self.calculate_delta(data["last_revision"], data["interval"])
            data["delta"] = delta
            data["ef"] = self.calculate_ease_factor(data["ef"], quality)
            data["interval"] = self.calculate_interval(
                chapter_id, data['interval'], data["ef"], quality
            )
            data["last_revision"] = now

        data["attempted"].extend([i["_id"] for i in practice_data])
        self.sr_db[user_id].update_one({"_id": chapter_id}, {"$set": data}, upsert=True)

    def get_chapters(self, user_id):
        chapters = list(self.sr_db[user_id].find({}, {"_id": 1, "ef": 1, "last_revision": 1, "interval": 1, "delta": 1}))
        return chapters
    
    def unique_questions_solved(self, user_id, chapter_id):
        data = self.sr_db[user_id].find_one({"_id": chapter_id})        
        ques = []
        activities = self.db.activities[user_id].find({"_id": {"$in": data.get("attempted", [])}}, {"details.question_id": 1})

        for activity in activities:
            q_id = activity['details']['question_id']
            if q_id not in ques:
                ques.append(q_id)
        return ques