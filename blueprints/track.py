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
    for q_id, question in db.pyqs['questions'].items():
        if question['exam'] == exam_id:
            if question['subject'] in [i['_id'] for i in subjects]:
                if question['subject'] not in questions:
                    questions[question['subject']] = 0
                questions[question['subject']] += 1
    for idx, subject in enumerate(subjects):
        subjects[idx]['question_count'] = questions.get(subject['_id'], 0)
    return render_template("track/exam.html", exam=exam, subjects=subjects, total_chapters=sum(len(s['chapters']) for s in subjects))