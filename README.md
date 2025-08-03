# 🚀 Planq – *Entrance Exam Prep. For Students, By Students*

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/database-MongoDB-brightgreen)](https://www.mongodb.com/)

---

## 📖 About Planq

Planq is a **self-built edtech platform** designed for **Indian entrance exam aspirants** (JEE, NEET, etc.).

### 🎯 What makes it unique?

- ✅ **Gamified Learning** → Streaks, XP, Achievements
- ✅ **Daily Tasks** → Duolingo-style health-based challenges
- ✅ **Spaced Repetition Engine** → AI-driven revision recommendations
- ✅ **AI Tutor** → PlanqAI (Gemini Flash 2.0 + RAG on question bank)
- ✅ **47k+ Curated Questions** → Custom tests, PYQs, analytics

---

## 📸 Screenshots
![home](/screenshots/home.png)

![search](/screenshots/search.png)

![achievements](/screenshots/achievements.png)

---

## 🛠 Tech Stack

| Layer        | Technology                                         |
| ------------ | -------------------------------------------------- |
| **Backend**  | Flask (Python)                                     |
| **Database** | MongoDB                                            |
| **Frontend** | Jinja2 Templates + Vanilla JS + CSS                |
| **AI API**   | Gemini Flash 2.0 via separate PlanqAI microservice |
| **RAG**      | FAISS + BM25 Hybrid Retrieval                      |

---

## 📂 Project Structure

```
planq/
├── blueprints/       # Modular Flask routes
│   ├── achievements.py   # Achievement system
│   ├── ai.py             # Handles PlanqAI API requests
│   ├── practice.py       # Daily task + streaks
│   ├── test.py           # Test generation & submission
│   ├── question.py       # Individual question attempts
│   └── ...               # Other route files
│
├── static/           # CSS, JS, Assets
│   ├── css/          # Page-specific styles
│   ├── js/           # Frontend logic
│   └── assets/       # Logo, favicon, images
│
├── templates/        # Jinja2 templates
│   ├── dashboard.html
│   ├── practice.html
│   ├── test_analysis.html
│   └── ...
│
├── utils/            # Helper modules
│   ├── __init__.py   # Generic utility methods
│   ├── database.py   # Database functions
│   ├── parser.py     # Parsing Questions to compress them
│   └── sr.py         # Spaced Repetition logic
│
├── main.py           # Entry point
├── config.py         # Exam configs & settings
├── requirements.txt  # Dependencies
└── vercel.json       # Deployment config
```

---

## 🚀 Getting Started

### 1️⃣ Clone the repo

```bash
git clone https://github.com/planq-org/planq.git
cd planq
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Configure environment (`.env`)

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=

MONGO_URI=
JWT_SECRET=
SECRET_KEY=

GEMINI_KEY=
RAG_ENDPOINT=
```

### 4️⃣ Run the app

```bash
python main.py
```

---

## 🎮 Features

### 🏆 **Gamification**

- ✔ 17 unlockable achievements
- ✔ XP & leveling system
- ✔ Daily tasks with health system

### 🧠 **Spaced Repetition**

- ✔ SM2-inspired interval algorithm
- ✔ Difficulty-aware retention
- ✔ Personalized revision suggestions

### 📚 **Tests & Questions**

- ✔ 47k+ curated questions
- ✔ PYQ practice mode
- ✔ AI-powered explanations (PlanqAI)

---

## 🧩 API Integration

Planq connects to a **separate AI microservice (PlanqAI)** that:
* ✅ Uses **Gemini Flash 2.0 + FAISS RAG**
* ✅ Returns **context-aware answers** based on the question bank

Example request from `ai.py`:

```python
response = requests.post(
    f"{os.getenv('RAG_ENDPOINT')}/retrieve",
    json={
        "token": token,
        "query": query,
        "exam_id": exam_id,
        "subject_id": subject_id,
        "top_k": top_k,
        "messages": messages
    }
)

result = response['results']
```

---

## 📅 Roadmap

* ✅ Streak system
* ✅ Achievements & XP
* ✅ Spaced repetition
* ✅ AI Tutor Integration (PlanqAI)
* ⏳ Social leaderboard & challenges
* ⏳ Flashcards & revision notes

---


Built **solo** by a student for students – with feedback from Reddit & Discord

If you like it → ⭐ Star this repo, it means a lot!
