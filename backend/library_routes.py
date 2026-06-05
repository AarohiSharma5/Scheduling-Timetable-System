"""
Library API (/api/library).

Staff (admin/principal/teacher):
  GET    /books                 List/search catalogue (?q=)
  POST   /books                 Add a book
  PUT    /books/<id>            Edit a book
  DELETE /books/<id>            Remove a book (only if no active loans)
  GET    /loans                 List loans (?status=issued|returned|overdue)
  POST   /loans                 Issue a book to a student
  POST   /loans/<id>/return     Mark a loan returned

Self-service:
  GET    /student/<id>          A student's loan history (student self / parent / staff)
"""

from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from models import db, Book, BookLoan, Student, Guardian
from jwt_utils import token_required, role_required

library_bp = Blueprint("library", __name__, url_prefix="/api/library")

_STAFF = ("admin", "principal", "teacher")


def _org_id():
    return (getattr(request, "user", {}) or {}).get("organization_id")


def _user_id():
    return (getattr(request, "user", {}) or {}).get("user_id")


def _role():
    return (getattr(request, "user", {}) or {}).get("role")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _student_name(s):
    return f"{s.first_name} {s.last_name}".strip() if s else None


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

@library_bp.route("/books", methods=["GET"])
@role_required(*_STAFF)
def list_books():
    q = Book.query.filter_by(organization_id=_org_id())
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(db.or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like)))
    return jsonify([b.to_dict() for b in q.order_by(Book.title).all()]), 200


@library_bp.route("/books", methods=["POST"])
@role_required(*_STAFF)
def create_book():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400
    try:
        copies = int(data.get("total_copies") or 1)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid copy count"}), 400
    copies = max(1, copies)
    book = Book(
        organization_id=_org_id(), title=title, author=(data.get("author") or None),
        isbn=(data.get("isbn") or None), category=(data.get("category") or None),
        total_copies=copies, available_copies=copies,
    )
    db.session.add(book)
    db.session.commit()
    return jsonify(book.to_dict()), 201


@library_bp.route("/books/<int:book_id>", methods=["PUT"])
@role_required(*_STAFF)
def update_book(book_id):
    book = Book.query.filter_by(id=book_id, organization_id=_org_id()).first()
    if not book:
        return jsonify({"error": "Book not found"}), 404
    data = request.get_json(silent=True) or {}
    on_loan = book.total_copies - book.available_copies
    for field in ("title", "author", "isbn", "category"):
        if field in data:
            setattr(book, field, (data[field] or None) if field != "title" else (data[field].strip() or book.title))
    if "total_copies" in data:
        try:
            new_total = max(on_loan, int(data["total_copies"]))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid copy count"}), 400
        book.total_copies = new_total
        book.available_copies = new_total - on_loan
    db.session.commit()
    return jsonify(book.to_dict()), 200


@library_bp.route("/books/<int:book_id>", methods=["DELETE"])
@role_required(*_STAFF)
def delete_book(book_id):
    book = Book.query.filter_by(id=book_id, organization_id=_org_id()).first()
    if not book:
        return jsonify({"error": "Book not found"}), 404
    active = BookLoan.query.filter_by(organization_id=_org_id(), book_id=book.id, status="issued").count()
    if active:
        return jsonify({"error": "Cannot delete a book that is currently issued"}), 400
    BookLoan.query.filter_by(organization_id=_org_id(), book_id=book.id).delete()
    db.session.delete(book)
    db.session.commit()
    return jsonify({"success": True}), 200


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

@library_bp.route("/loans", methods=["GET"])
@role_required(*_STAFF)
def list_loans():
    loans = BookLoan.query.filter_by(organization_id=_org_id()).order_by(BookLoan.id.desc()).all()
    status = request.args.get("status")
    if status == "overdue":
        loans = [l for l in loans if l.is_overdue()]
    elif status:
        loans = [l for l in loans if l.status == status]
    books = {b.id: b.title for b in Book.query.filter_by(organization_id=_org_id()).all()}
    sids = {l.student_id for l in loans}
    students = {s.id: _student_name(s) for s in Student.query.filter(Student.id.in_(sids or [-1])).all()}
    return jsonify([l.to_dict(book_title=books.get(l.book_id),
                              student_name=students.get(l.student_id)) for l in loans]), 200


@library_bp.route("/loans", methods=["POST"])
@role_required(*_STAFF)
def issue_book():
    data = request.get_json(silent=True) or {}
    book = Book.query.filter_by(id=data.get("book_id"), organization_id=_org_id()).first()
    if not book:
        return jsonify({"error": "Book not found"}), 404
    student = Student.query.filter_by(id=data.get("student_id"), organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    if book.available_copies <= 0:
        return jsonify({"error": "No copies available"}), 400

    issued = _parse_date(data.get("issued_on")) or datetime.utcnow().date()
    due = _parse_date(data.get("due_on")) or (issued + timedelta(days=14))
    loan = BookLoan(
        organization_id=_org_id(), book_id=book.id, student_id=student.id,
        issued_on=issued, due_on=due, status="issued", created_by=_user_id(),
    )
    book.available_copies -= 1
    db.session.add(loan)
    db.session.commit()
    return jsonify(loan.to_dict(book_title=book.title, student_name=_student_name(student))), 201


@library_bp.route("/loans/<int:loan_id>/return", methods=["POST"])
@role_required(*_STAFF)
def return_book(loan_id):
    loan = BookLoan.query.filter_by(id=loan_id, organization_id=_org_id()).first()
    if not loan:
        return jsonify({"error": "Loan not found"}), 404
    if loan.status == "returned":
        return jsonify({"error": "Already returned"}), 400
    loan.status = "returned"
    loan.returned_on = datetime.utcnow().date()
    book = Book.query.get(loan.book_id)
    if book:
        book.available_copies = min(book.total_copies, book.available_copies + 1)
    db.session.commit()
    return jsonify(loan.to_dict(book_title=book.title if book else None)), 200


@library_bp.route("/my", methods=["GET"])
@role_required("student")
def my_loans():
    student = Student.query.filter_by(organization_id=_org_id(), user_id=_user_id()).first()
    if not student:
        return jsonify({"error": "No student record is linked to your account"}), 404
    return student_loans(student.id)


@library_bp.route("/student/<int:student_id>", methods=["GET"])
@token_required
def student_loans(student_id):
    student = Student.query.filter_by(id=student_id, organization_id=_org_id()).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404

    role = _role()
    if role in _STAFF:
        pass
    elif role == "student" and student.user_id == _user_id():
        pass
    elif role == "parent" and Guardian.query.filter_by(
            organization_id=_org_id(), user_id=_user_id(), student_id=student.id).first():
        pass
    else:
        return jsonify({"error": "Not allowed"}), 403

    loans = BookLoan.query.filter_by(organization_id=_org_id(), student_id=student_id).order_by(BookLoan.id.desc()).all()
    books = {b.id: b.title for b in Book.query.filter_by(organization_id=_org_id()).all()}
    return jsonify({
        "student": {"id": student.id, "name": _student_name(student)},
        "loans": [l.to_dict(book_title=books.get(l.book_id)) for l in loans],
    }), 200
