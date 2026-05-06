from flask import Blueprint, request, jsonify
from models import db, Plan, User
from planner_service import PlannerService
from datetime import datetime

api = Blueprint("api", __name__, url_prefix="/api")

@api.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "API is running"}), 200

@api.route("/sample-data", methods=["GET"])
def get_sample_data():
    return jsonify({
        "school_profile": {
            "institution_name": "Sample High School", "days_per_week": 5,
            "periods_per_day": 6, "student_count": 500, "core_subjects_target": 5, "elective_limit": 3,
        },
        "teachers": [
            {"id": 1, "name": "Dr. Smith", "contact_hours": 24, "expertise": ["Mathematics"]},
            {"id": 2, "name": "Ms. Johnson", "contact_hours": 24, "expertise": ["English"]},
        ],
        "subjects": [
            {"id": 1, "name": "Mathematics", "teacher_id": 1, "is_core": True, "periods_required": 4},
            {"id": 2, "name": "English", "teacher_id": 2, "is_core": True, "periods_required": 3},
        ],
    }), 200

@api.route("/plans", methods=["POST"])
def create_plan():
    try:
        data = request.get_json()
        plan = Plan(
            user_id=1, title=data.get("title", "Untitled"),
            description=data.get("description", ""),
            school_profile=data.get("school_profile", {}),
            teachers=data.get("teachers", []),
            subjects=data.get("subjects", []),
        )
        db.session.add(plan)
        db.session.commit()
        return jsonify(plan.to_dict(include_details=True)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route("/plans", methods=["GET"])
def list_plans():
    plans = Plan.query.filter_by(user_id=1).order_by(Plan.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in plans]), 200

@api.route("/plans/<int:plan_id>", methods=["GET"])
def get_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    return jsonify(plan.to_dict(include_details=True)), 200

@api.route("/plans/<int:plan_id>", methods=["PUT"])
def update_plan(plan_id):
    try:
        plan = Plan.query.get_or_404(plan_id)
        data = request.get_json()
        if "title" in data: plan.title = data["title"]
        if "school_profile" in data: plan.school_profile = data["school_profile"]
        if "teachers" in data: plan.teachers = data["teachers"]
        if "subjects" in data: plan.subjects = data["subjects"]
        plan.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(plan.to_dict(include_details=True)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route("/plans/<int:plan_id>", methods=["DELETE"])
def delete_plan(plan_id):
    try:
        plan = Plan.query.get_or_404(plan_id)
        db.session.delete(plan)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route("/plans/<int:plan_id>/generate", methods=["POST"])
def generate_timetable(plan_id):
    try:
        plan = Plan.query.get_or_404(plan_id)
        timetable, warnings = PlannerService.build_timetable(
            plan.school_profile, plan.teachers, plan.subjects
        )
        plan.timetable, plan.warnings, plan.status = timetable, warnings, "completed"
        plan.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"plan_id": plan_id, "timetable": timetable, "warnings": warnings}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api.route("/plans/<int:plan_id>/export/csv", methods=["GET"])
def export_csv(plan_id):
    try:
        plan = Plan.query.get_or_404(plan_id)
        if not plan.timetable:
            return jsonify({"error": "No timetable"}), 400
        lines = [f"Timetable - {plan.title}", "", f"School: {plan.school_profile.get('institution_name', 'N/A')}", ""]
        lines.append("Day," + ",".join([f"Period {i+1}" for i in range(len(plan.timetable[0]))]))
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        for day_idx, day_data in enumerate(plan.timetable):
            row = [days[day_idx % len(days)]]
            for slot in day_data:
                row.append(f"{slot['subject']} ({slot['teacher']})" if slot else "")
            lines.append(",".join(row))
        csv_content = "\n".join(lines)
        return csv_content, 200, {"Content-Type": "text/csv", "Content-Disposition": f"attachment; filename=timetable_{plan_id}.csv"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500
