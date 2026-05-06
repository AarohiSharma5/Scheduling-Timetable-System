from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plans = db.relationship("Plan", backref="creator", lazy=True)
    
    def to_dict(self):
        return {"id": self.id, "email": self.email, "username": self.username}

class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    school_profile = db.Column(db.JSON, nullable=False)
    teachers = db.Column(db.JSON, default=list)
    subjects = db.Column(db.JSON, default=list)
    timetable = db.Column(db.JSON)
    warnings = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_details=False):
        result = {
            "id": self.id, "user_id": self.user_id, "title": self.title,
            "description": self.description, "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_details:
            result.update({
                "school_profile": self.school_profile, "teachers": self.teachers,
                "subjects": self.subjects, "timetable": self.timetable,
                "warnings": self.warnings,
            })
        return result
