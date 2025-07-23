from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)
from sr import SR
from database import Database
from utils import auth_required, ist_now
import math
from datetime import timedelta

track_bp = Blueprint("track", __name__, url_prefix="/track")

db: Database = None
sr: SR = None


def init_blueprint(database, spaced_repetition):
    global db, sr
    db = database
    sr = spaced_repetition
    return track_bp


@auth_required
@track_bp.route("/<exam_id>")
def progress(exam_id):
    exam = db.get_exam(exam_id)
    if not exam:
        flash("Exam not found", "error")
        return redirect(url_for("dashboard"))

    subjects = db.get_subjects(exam_id, full=True)
    questions = {}
    for q_id, question in db.pyqs["questions"].items():
        if question["exam"] == exam_id:
            if question["subject"] in [i["_id"] for i in subjects]:
                if question["subject"] not in questions:
                    questions[question["subject"]] = 0
                questions[question["subject"]] += 1
    for idx, subject in enumerate(subjects):
        subjects[idx]["question_count"] = questions.get(subject["_id"], 0)
    return render_template(
        "track/exam.html",
        exam=exam,
        subjects=subjects,
        total_chapters=sum(len(s["chapters"]) for s in subjects),
    )


@auth_required
@track_bp.route("/<exam_id>/<subject_id>")
def chapters(exam_id, subject_id):
    exam = db.get_exam(exam_id)
    if not exam:
        flash("Exam not found", "error")
        return redirect(url_for("dashboard"))

    subject = db.get_subject(subject_id)
    if not subject:
        flash("Subject not found", "error")
        return redirect(url_for("track.progress", exam_id=exam_id))

    chapters = db.get_chapters(subject_id)
    # Create a dictionary to store question counts per chapter
    chapter_counts = {}
    for q_id, question in db.pyqs["questions"].items():
        chapter_id = question.get("chapter")
        if chapter_id:
            chapter_counts[chapter_id] = chapter_counts.get(chapter_id, 0) + 1

    # Assign counts to chapters
    for idx, chapter in enumerate(chapters):
        chapters[idx]["question_count"] = chapter_counts.get(chapter["_id"], 0)
        diff = sr.ch_data.get(chapter["_id"], {}).get("level", 0)
        if diff < 1.7:
            chapters[idx]["difficulty"] = "Easy"
        elif diff < 2.1:
            chapters[idx]["difficulty"] = "Medium"
        else:
            chapters[idx]["difficulty"] = "Hard"
    return render_template(
        "track/chapter.html",
        exam=exam,
        subject=subject,
        chapters=chapters,
        total_questions=sum(ch.get("question_count", 0) for ch in chapters),
    )


@auth_required
@track_bp.route("/<exam_id>/<subject_id>/<chapter_id>")
def chapter_detail(exam_id, subject_id, chapter_id):
    exam = db.get_exam(exam_id)
    if not exam:
        flash("Exam not found", "error")
        return redirect(url_for("dashboard"))

    subject = db.get_subject(subject_id)
    if not subject:
        flash("Subject not found", "error")
        return redirect(url_for("track.progress", exam_id=exam_id))

    chapter = db.get_chapter(chapter_id)
    if not chapter:
        flash("Chapter not found", "error")
        return redirect(
            url_for("track.chapters", exam_id=exam_id, subject_id=subject_id)
        )

    questions = db.get_questions(chapter_id)
    ch_data = sr.ch_data.get(chapter_id, {})
    sr_data = sr.sr_db[session["user"]["id"]].find_one({"_id": chapter_id})
    
    if sr_data:
        attempts = list(
            db.activities[session["user"]["id"]].find(
                {"_id": {"$in": sr_data.get("attempted", [])}}
            )
        )
        attempts = [
            {
                "question_id": a["details"]["question_id"],
                "is_correct": a["details"]["is_correct"],
                "time_taken": a["details"]["time_taken"],
                "timestamp": a["timestamp"].isoformat(),
            }
            for a in attempts
        ]
    else:
        attempts = []
    correct = 0
    incorrect = 0
    individual_attempts = {}
    for attempt in attempts:
        q_id = attempt["question_id"]
        if q_id not in individual_attempts:
            individual_attempts[q_id] = []
        individual_attempts[q_id].append(attempt)
        if attempt["is_correct"]:
            correct += 1
        else:
            incorrect += 1

    return render_template(
        "track/chapter_detail.html",
        exam=exam,
        subject=subject,
        chapter=chapter,
        questions=questions,
        attempts=attempts,
        individual_attempts=individual_attempts,
        ch_data=ch_data,
        sr_data=sr_data,
        accuracy_data = {
            "correct": correct,
            "incorrect": incorrect,
            "total": correct + incorrect,
            "accuracy": (correct / (correct + incorrect) * 100) if (correct + incorrect) > 0 else 0
        },
        math=math,
        timedelta=timedelta,
        ist_now=ist_now
    )

@track_bp.route("/chapter/<chapter_id>")
def chapter_redirect(chapter_id):
    chapter = db.get_chapter(chapter_id)
    return redirect(url_for("track.chapter_detail", exam_id=chapter["exam"], subject_id=chapter["subject"], chapter_id=chapter["_id"]))