"""
Data-subject-rights and retention helpers (DPDP/GDPR).

* student_data_export: a portable bundle of everything we hold on one student
  (right of access / data portability).
* anonymize_student: irreversibly strips PII while keeping de-identified
  academic records intact for referential integrity (right to erasure).
"""

from datetime import datetime


# PII fields cleared on erasure. Keep in sync with the encrypted columns + DOB.
_PII_FIELDS = (
    "email", "father_name", "mother_name", "contact_number",
    "address", "blood_group", "date_of_birth", "gender",
)


def student_data_export(student):
    """Full record bundle for a single student (access / portability)."""
    from models import AttendanceRecord, Mark, FeeInvoice, Payment, AssignmentSubmission

    sid = student.id

    def dump(rows):
        return [r.to_dict() for r in rows]

    attendance = AttendanceRecord.query.filter_by(student_id=sid).all()
    marks = Mark.query.filter_by(student_id=sid).all()
    invoices = FeeInvoice.query.filter_by(student_id=sid).all()
    payments = Payment.query.filter_by(student_id=sid).all()
    submissions = AssignmentSubmission.query.filter_by(student_id=sid).all()

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "subject": "student",
        "profile": student.to_dict(),
        "records": {
            "attendance": dump(attendance),
            "marks": dump(marks),
            "fee_invoices": dump(invoices),
            "payments": dump(payments),
            "assignment_submissions": dump(submissions),
        },
        "counts": {
            "attendance": len(attendance),
            "marks": len(marks),
            "fee_invoices": len(invoices),
            "payments": len(payments),
            "assignment_submissions": len(submissions),
        },
    }


def anonymize_student(student):
    """Irreversibly remove PII, keeping academic records de-identified.

    student_id / admission_no / class are retained so historical attendance and
    marks stay referentially valid but can no longer be tied to a real person.
    """
    student.first_name = "Redacted"
    student.last_name = f"Student-{student.id}"
    student.email = None
    student.father_name = None
    student.mother_name = None
    student.contact_number = None
    student.address = None
    student.blood_group = None
    student.date_of_birth = None
    student.gender = None
    student.status = "Anonymized"
    student.consent_given = False
    student.consent_at = None
    student.consent_by = None
    student.updated_at = datetime.utcnow()
    return student
