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
            penalty = 0.1 + 0.05*(level-1)
            bonus = 0.05 + 0.03*(level-1)

            self.ch_data[ch] = {
                "_id": ch,
                "name": diff['name'],
                "count": diff['question_count'],
                "level": level,
                "dr": decay_rate,
                "rt": revision_threshold,
                "penalty": penalty,
                "bonus": bonus 
            }
