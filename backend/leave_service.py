"""
Leave Management Service

Handles:
- Leave request creation and approval
- Substitute teacher recommendation
- Timetable adjustment for absent teachers
- Notification generation
"""

from datetime import datetime, timedelta
from models import db, LeaveRequest, Teacher, TimetableSlot, Timetable, Notification, User
from sqlalchemy import and_, or_


class LeaveService:
    """Service for managing teacher leaves and substitutes"""
    
    @staticmethod
    def request_leave(teacher_id, leave_date, reason, leave_type="casual"):
        """Create a new leave request"""
        try:
            # Check if leave request already exists for this date
            existing = LeaveRequest.query.filter_by(
                teacher_id=teacher_id,
                leave_date=leave_date,
                status="pending"
            ).first()
            
            if existing:
                return {"success": False, "error": "Leave request already pending for this date"}
            
            # Inherit the org from the requesting teacher so the leave stays scoped.
            teacher = Teacher.query.get(teacher_id)
            org_id = teacher.organization_id if teacher else None

            # Create leave request
            leave_request = LeaveRequest(
                organization_id=org_id,
                teacher_id=teacher_id,
                leave_date=leave_date,
                reason=reason,
                leave_type=leave_type,
                status="pending"
            )
            
            db.session.add(leave_request)
            db.session.commit()
            
            # Notify admin/principal
            LeaveService._notify_leave_request(leave_request)
            
            return {"success": True, "leave_request_id": leave_request.id}
        
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def approve_leave(leave_request_id, approved_by_id, substitute_teacher_id=None, auto_adjust=True):
        """Approve a leave request and optionally assign substitute"""
        try:
            leave_request = LeaveRequest.query.get(leave_request_id)
            if not leave_request:
                return {"success": False, "error": "Leave request not found"}
            
            # Check if substitute is available for the specific periods we need
            if substitute_teacher_id:
                day_name = leave_request.leave_date.strftime('%A')
                busy_periods = {
                    s.period_number
                    for s in TimetableSlot.query.filter_by(
                        teacher_id=leave_request.teacher_id, day=day_name
                    ).all()
                }
                if not LeaveService._is_substitute_available(substitute_teacher_id, leave_request.leave_date, busy_periods):
                    return {"success": False, "error": "Selected substitute has conflicting classes on that day"}
            else:
                # Find best available substitute
                substitute = LeaveService._find_best_substitute(leave_request)
                if substitute:
                    substitute_teacher_id = substitute.id
            
            # Update leave request
            leave_request.status = "approved"
            leave_request.approved_by = approved_by_id
            leave_request.substitute_teacher_id = substitute_teacher_id
            
            # Adjust timetable if auto_adjust is True
            if auto_adjust:
                adjustments = LeaveService._adjust_timetable_for_leave(leave_request)
                leave_request.timetable_adjustments = adjustments
            
            db.session.commit()
            
            # Create notifications
            LeaveService._notify_leave_approval(leave_request)
            
            return {
                "success": True,
                "leave_request": leave_request.to_dict(),
                "substitute_teacher_id": substitute_teacher_id
            }
        
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def reject_leave(leave_request_id, rejection_reason):
        """Reject a leave request"""
        try:
            leave_request = LeaveRequest.query.get(leave_request_id)
            if not leave_request:
                return {"success": False, "error": "Leave request not found"}
            
            leave_request.status = "rejected"
            leave_request.rejection_reason = rejection_reason
            db.session.commit()
            
            # Notify teacher
            LeaveService._notify_leave_rejection(leave_request)
            
            return {"success": True, "leave_request": leave_request.to_dict()}
        
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _find_best_substitute(leave_request):
        """Find the best available substitute teacher for a leave request"""
        teacher = Teacher.query.get(leave_request.teacher_id)
        if not teacher:
            return None
        
        # Find teachers who:
        # 1. Can teach the same subjects
        # 2. Are available on that date (no conflicting classes)
        # 3. Have the lowest teaching load that day
        
        available_substitutes = []
        
        # The periods the absent teacher must be covered for that day. A valid
        # substitute must be free during *these* periods (not merely have an
        # empty day).
        day_name = leave_request.leave_date.strftime('%A')
        busy_periods = {
            s.period_number
            for s in TimetableSlot.query.filter_by(
                teacher_id=teacher.id, day=day_name
            ).all()
        }

        # Only consider substitutes inside the same organization.
        org_id = teacher.organization_id

        # subject_ids is a JSON column, so we can't use SQL LIKE/contains on it
        # (Postgres rejects `json ~~ text`). Filter subject overlap in Python.
        wanted_subjects = {str(s) for s in (teacher.subject_ids or [])}

        seen = set()
        candidates = Teacher.query.filter(
            Teacher.id != teacher.id,
            Teacher.organization_id == org_id,
        ).all()

        for sub in candidates:
            if sub.id in seen:
                continue
            sub_subjects = {str(s) for s in (sub.subject_ids or [])}
            # Must be able to teach at least one of the absent teacher's subjects.
            if not (wanted_subjects & sub_subjects):
                continue
            seen.add(sub.id)
            if LeaveService._is_substitute_available(sub.id, leave_request.leave_date, busy_periods):
                # Count their teaching load on that day (prefer the freest)
                load = TimetableSlot.query.filter_by(
                    teacher_id=sub.id
                ).filter(
                    TimetableSlot.day == day_name
                ).count()

                available_substitutes.append((sub, load))
        
        # Return same-subject substitute with the lowest load.
        if available_substitutes:
            available_substitutes.sort(key=lambda x: x[1])
            return available_substitutes[0][0]

        # Fallback: no free same-subject teacher. In a real school any free
        # teacher covers the class (supervision/cover). Pick the freest teacher
        # in the org who is available during the required periods.
        fallback = []
        for sub in candidates:
            if LeaveService._is_substitute_available(sub.id, leave_request.leave_date, busy_periods):
                load = TimetableSlot.query.filter_by(teacher_id=sub.id).filter(
                    TimetableSlot.day == day_name
                ).count()
                fallback.append((sub, load))

        if fallback:
            fallback.sort(key=lambda x: x[1])
            return fallback[0][0]

        return None
    
    @staticmethod
    def _is_substitute_available(teacher_id, date, busy_periods=None):
        """Check whether a teacher can cover the given periods on a date.

        A substitute is available only if they are not themselves on approved
        leave that day AND they have no class of their own during the periods
        that need covering. The old version computed the class conflict and then
        threw it away, which silently double-booked substitutes.
        """
        day_name = date.strftime('%A')

        # Already on approved leave that day → unavailable.
        has_leave = LeaveRequest.query.filter_by(
            teacher_id=teacher_id,
            leave_date=date,
            status="approved"
        ).first()
        if has_leave:
            return False

        # Busy during one of the required periods → would be double-booked.
        if busy_periods:
            conflict = TimetableSlot.query.filter(
                TimetableSlot.teacher_id == teacher_id,
                TimetableSlot.day == day_name,
                TimetableSlot.period_number.in_(list(busy_periods))
            ).first()
            if conflict:
                return False

        return True
    
    @staticmethod
    def _adjust_timetable_for_leave(leave_request):
        """Adjust timetable slots for absent teacher"""
        adjustments = {
            "original_slots": [],
            "adjustments": []
        }
        
        try:
            day_name = leave_request.leave_date.strftime('%A')
            
            # Get all slots for this teacher on the absent day
            slots = TimetableSlot.query.filter_by(
                teacher_id=leave_request.teacher_id,
                day=day_name
            ).all()
            
            adjustments["original_slots"] = [s.to_dict() for s in slots]
            
            # Option 1: Assign to substitute (if found)
            if leave_request.substitute_teacher_id:
                for slot in slots:
                    old_data = {
                        "slot_id": slot.id,
                        "day": slot.day,
                        "period": slot.period_number,
                        "batch_id": slot.batch_id,
                        "subject_id": slot.subject_id,
                        "old_teacher_id": slot.teacher_id
                    }
                    
                    slot.teacher_id = leave_request.substitute_teacher_id
                    old_data["new_teacher_id"] = leave_request.substitute_teacher_id
                    adjustments["adjustments"].append(old_data)
            
            # Option 2: If no substitute, mark as substitute needed in notes
            else:
                for slot in slots:
                    slot.is_lunch = False  # Temporarily mark
                    adjustments["adjustments"].append({
                        "slot_id": slot.id,
                        "status": "needs_substitute",
                        "notice": "No suitable substitute found - may need manual intervention"
                    })
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            adjustments["error"] = str(e)
        
        return adjustments
    
    @staticmethod
    def mark_teacher_absent(teacher_id, date, approved_by=None, substitute_teacher_id=None):
        """Mark a teacher as absent for a specific date (without prior leave request).

        If ``substitute_teacher_id`` is provided it is used (after validating the
        chosen teacher is free during the absent teacher's periods that day),
        otherwise the best available substitute is auto-assigned.
        """
        try:
            teacher = Teacher.query.get(teacher_id)
            # Create implicit leave request
            leave_request = LeaveRequest(
                organization_id=teacher.organization_id if teacher else None,
                teacher_id=teacher_id,
                leave_date=date,
                reason="Marked absent by administrator",
                leave_type="unplanned",
                status="approved",
                approved_by=approved_by  # the admin/principal who marked it
            )

            db.session.add(leave_request)
            db.session.commit()

            # Determine the substitute: manual selection (validated) or auto.
            chosen_sub_id = None
            if substitute_teacher_id:
                day_name = date.strftime('%A')
                busy_periods = {
                    s.period_number
                    for s in TimetableSlot.query.filter_by(
                        teacher_id=teacher_id, day=day_name
                    ).all()
                }
                if not LeaveService._is_substitute_available(substitute_teacher_id, date, busy_periods):
                    db.session.delete(leave_request)
                    db.session.commit()
                    return {"success": False, "error": "Selected substitute has conflicting classes on that day"}
                chosen_sub_id = substitute_teacher_id
            else:
                substitute = LeaveService._find_best_substitute(leave_request)
                if substitute:
                    chosen_sub_id = substitute.id

            if chosen_sub_id:
                leave_request.substitute_teacher_id = chosen_sub_id
                adjustments = LeaveService._adjust_timetable_for_leave(leave_request)
                leave_request.timetable_adjustments = adjustments
                db.session.commit()
            
            # Notify everyone
            LeaveService._notify_teacher_absent(leave_request)
            
            return {
                "success": True,
                "leave_request": leave_request.to_dict(),
                "substitute_teacher_id": leave_request.substitute_teacher_id
            }
        
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_leave_requests(filters=None):
        """Get leave requests with optional filters"""
        query = LeaveRequest.query
        
        if filters:
            if filters.get("organization_id"):
                query = query.filter_by(organization_id=filters["organization_id"])
            if filters.get("teacher_id"):
                query = query.filter_by(teacher_id=filters["teacher_id"])
            if filters.get("status"):
                query = query.filter_by(status=filters["status"])
            if filters.get("leave_type"):
                query = query.filter_by(leave_type=filters["leave_type"])
            if filters.get("from_date"):
                from_date = datetime.fromisoformat(filters["from_date"]).date()
                query = query.filter(LeaveRequest.leave_date >= from_date)
            if filters.get("to_date"):
                to_date = datetime.fromisoformat(filters["to_date"]).date()
                query = query.filter(LeaveRequest.leave_date <= to_date)
        
        return query.order_by(LeaveRequest.created_at.desc()).all()
    
    # ========================================================================
    # NOTIFICATION HELPERS
    # ========================================================================
    
    @staticmethod
    def _notify_leave_request(leave_request):
        """Notify admin/principal of new leave request"""
        org_id = leave_request.organization_id
        admin_users = User.query.filter_by(role="admin", organization_id=org_id).all()
        principal_users = User.query.filter_by(role="principal", organization_id=org_id).all()
        approvers = admin_users + principal_users
        
        teacher = Teacher.query.get(leave_request.teacher_id)
        teacher_name = teacher.name if teacher else "Unknown Teacher"
        
        for user in approvers:
            notification = Notification(
                user_id=user.id,
                title="New Leave Request",
                message=f"{teacher_name} has requested leave on {leave_request.leave_date.strftime('%d %B %Y')} ({leave_request.leave_type})",
                notification_type="leave_request_pending",
                related_id=leave_request.id,
                action_url=f"/admin/leaves/{leave_request.id}"
            )
            db.session.add(notification)
        
        db.session.commit()
    
    @staticmethod
    def _notify_leave_approval(leave_request):
        """Notify teacher and affected batches of leave approval"""
        teacher = Teacher.query.get(leave_request.teacher_id)
        teacher_user = User.query.filter_by(email=teacher.email).first()
        
        if teacher_user:
            message = f"Your leave request for {leave_request.leave_date.strftime('%d %B %Y')} has been approved"
            if leave_request.substitute_teacher_id:
                substitute = Teacher.query.get(leave_request.substitute_teacher_id)
                message += f". {substitute.name} will take your classes."
            
            notification = Notification(
                user_id=teacher_user.id,
                title="Leave Approved",
                message=message,
                notification_type="leave_approved",
                related_id=leave_request.id,
                action_url=f"/teacher/leaves/{leave_request.id}"
            )
            db.session.add(notification)
        
        # Notify students (affected batches)
        day_name = leave_request.leave_date.strftime('%A')
        affected_slots = TimetableSlot.query.filter_by(
            teacher_id=leave_request.teacher_id,
            day=day_name
        ).all()
        
        affected_batch_ids = set(s.batch_id for s in affected_slots if s.batch_id)
        
        for batch_id in affected_batch_ids:
            students = User.query.filter_by(
                batch_id=batch_id, role="student", organization_id=leave_request.organization_id
            ).all()
            for student in students:
                message = f"Class on {leave_request.leave_date.strftime('%d %B %Y')} will have a substitute teacher."
                if leave_request.substitute_teacher_id:
                    substitute = Teacher.query.get(leave_request.substitute_teacher_id)
                    message = f"Class on {leave_request.leave_date.strftime('%d %B %Y')} will be handled by {substitute.name}."
                
                notification = Notification(
                    user_id=student.id,
                    title="Class Teacher Change",
                    message=message,
                    notification_type="teacher_substituted",
                    related_id=leave_request.id,
                    action_url=f"/student/timetable"
                )
                db.session.add(notification)
        
        db.session.commit()
    
    @staticmethod
    def _notify_leave_rejection(leave_request):
        """Notify teacher of leave rejection"""
        teacher = Teacher.query.get(leave_request.teacher_id)
        teacher_user = User.query.filter_by(email=teacher.email).first()
        
        if teacher_user:
            notification = Notification(
                user_id=teacher_user.id,
                title="Leave Request Rejected",
                message=f"Your leave request for {leave_request.leave_date.strftime('%d %B %Y')} was rejected. Reason: {leave_request.rejection_reason}",
                notification_type="leave_rejected",
                related_id=leave_request.id,
                action_url=f"/teacher/leaves/{leave_request.id}"
            )
            db.session.add(notification)
            db.session.commit()
    
    @staticmethod
    def _notify_teacher_absent(leave_request):
        """Notify everyone when teacher is marked absent"""
        teacher = Teacher.query.get(leave_request.teacher_id)
        teacher_name = teacher.name if teacher else "Unknown Teacher"
        
        # Notify all users in the same organization about the change
        all_users = User.query.filter_by(organization_id=leave_request.organization_id).all()
        for user in all_users:
            if user.role in ["admin", "principal", "teacher"]:
                message = f"{teacher_name} has been marked absent on {leave_request.leave_date.strftime('%d %B %Y')}"
                if leave_request.substitute_teacher_id:
                    substitute = Teacher.query.get(leave_request.substitute_teacher_id)
                    message += f". {substitute.name} will cover the classes."
                
                notification = Notification(
                    user_id=user.id,
                    title="Teacher Absent",
                    message=message,
                    notification_type="teacher_absent",
                    related_id=leave_request.id,
                    action_url=f"/admin/leaves/{leave_request.id}"
                )
                db.session.add(notification)
        
        db.session.commit()
