from utils import generate_ch_difficulty
from database import Database
import math

class SR:
    def __init__(self, db: Database):
        self.db = db

        self.difficulty = generate_ch_difficulty(
            self.db.pyqs['chapters'], 
            self.db.pyqs['questions']
        )

        self.ch_data = {}

        for ch, diff in self.difficulty:
            level = diff['average_level']
            decay_rate = 1 + 0.1*(level - 1)
            revision_threshold = min(25, max(5, 0.15*diff['question_count']))
            ease_factor = 2.5 - (0.3 * (level-1))
            penalty = 0.1 + 0.05*(level-1)
            bonus = 0.05 + 0.03*(level-1)

            self.ch_data[ch] = {
                "_id": ch,
                "name": diff['name'],
                "count": diff['question_count'],
                "level": level,
                "dr": decay_rate,
                "rt": revision_threshold,
                "ef": ease_factor,
                "penalty": penalty,
                "bonus": bonus,
            }

        self.meta = {
            "easy": {
                "avg_time": 60000,
                "q_amt": 0.4
            },
            "med": {
                "avg_time": 180000,
                "q_amt": 0.4
            },
            "hard": {
                "avg_time": 300000,
                "q_amt": 0.2
            },
        }

        self.sr_db = self.db.client['sr']

    def calculate_quality(self, status, time):
        if (time < 5000 and status == False) or status == None:
            return 0
        if status == False:
            return 1
        else:
            if time < 10000:
                return 3
            else:
                return 2
            
    def calculate_interval(self, chapter_id, last_interval, ef, quality):
        if quality <= 1.5:
            return last_interval * (ef - self.ch_data[chapter_id]['penalty'])
        elif quality >= 2.5:
            return last_interval * (ef + self.ch_data[chapter_id]['bonus'])
        else:
            return last_interval * ef
        
    def calculate_retention(self, last_revision, interval, chapter_id):
        retention = math.exp((-self.ch_data[chapter_id]['dr']*last_revision)/interval)
        return retention
    
    def calculate_ease_factor(self, ef_old, quality):
        ef_new = ef_old + (0.1-(3-quality) * (0.08 + (3-quality) * 0.02))
        return ef_new