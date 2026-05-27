# 🚀 New Features Guide - PDF Export, Leave Management, Notifications

Complete guide for the three new features added to your school timetable app.

---

## 1. 📄 PDF Export (Printable Timetables)

### Overview
Generate professional A4-sized PDF exports of timetables in two formats:
- **Batch-wise**: One grade/section per page
- **Teacher-wise**: One teacher per page

### Features
✅ School header with name and date  
✅ Color-coded layout  
✅ Professional typography  
✅ Lunch breaks clearly marked  
✅ Perfect for printing and distribution  

### How to Use

#### Backend Implementation (Complete ✅)
- **File**: `backend/pdf_utils.py`
- **Method**: `export_batch_timetable()` and `export_teacher_timetable()`
- **Dependencies**: reportlab, WeasyPrint, Pillow

#### Frontend Integration Example

```typescript
// src/api.ts
export const timetableAPI = {
  // Download batch-wise PDF
  exportBatchPDF: (timetableId: number) =>
    axiosInstance.get(`/export/timetable/batch/${timetableId}`, {
      responseType: 'blob'
    }),

  // Download teacher-wise PDF
  exportTeacherPDF: (timetableId: number) =>
    axiosInstance.get(`/export/timetable/teacher/${timetableId}`, {
      responseType: 'blob'
    })
};

// Usage in component
const downloadPDF = async (timetableId: number, type: 'batch' | 'teacher') => {
  try {
    const response = type === 'batch' 
      ? await timetableAPI.exportBatchPDF(timetableId)
      : await timetableAPI.exportTeacherPDF(timetableId);

    // Create download link
    const url = window.URL.createObjectURL(response);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `timetable_${type}_${timetableId}.pdf`);
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('PDF export failed:', error);
  }
};
```

#### API Endpoint
```
GET /api/export/timetable/batch/{timetable_id}
GET /api/export/timetable/teacher/{timetable_id}

Authorization Required: Bearer token
Roles Allowed: admin, principal
```

#### Sample Output
```
┌─────────────────────────────────────────────┐
│         St. Xavier's School                 │
│   Timetable: May 2026 Schedule              │
│   Generated on: 25 May 2026 at 14:30        │
├─────────────────────────────────────────────┤
│ Grade 9 - Section A                         │
├──────────┬──────────┬──────────┬────────────┤
│ Period   │ Monday   │ Tuesday  │ Wednesday  │
├──────────┼──────────┼──────────┼────────────┤
│Period 1  │ English  │ Math     │ English    │
│ (08:00)  │(Priya)   │(Rajesh)  │(Priya)     │
├──────────┼──────────┼──────────┼────────────┤
│Period 2  │ Math     │ Physics  │ History    │
│ (08:45)  │(Rajesh)  │(Anjali)  │(Meera)     │
├──────────┼──────────┼──────────┼────────────┤
│Period 3  │ Physics  │ Chemistry│ Math       │
│ (09:30)  │(Anjali)  │(Anjali)  │(Rajesh)    │
├──────────┼──────────┼──────────┼────────────┤
│Period 4  │ Biology  │ English  │ Biology    │
│ (10:15)  │(Vikram)  │(Priya)   │(Vikram)    │
├──────────┼──────────┼──────────┼────────────┤
│ LUNCH    │ LUNCH    │ LUNCH    │ LUNCH      │
│(12:00)   │          │          │            │
└──────────┴──────────┴──────────┴────────────┘
```

---

## 2. 🏥 Leave Management (Teacher Absence & Substitution)

### Overview
Complete system for managing teacher leaves with automatic substitute assignment and timetable adjustment.

### Features
✅ Teacher leave requests with reason  
✅ Leave types: sick, casual, emergency, other  
✅ Admin approval workflow  
✅ Automatic substitute recommendation  
✅ Timetable auto-adjustment  
✅ One-day emergency absence marking  
✅ Comprehensive timetable history  

### Workflow

```
┌─────────────────────────────────────┐
│ Teacher Requests Leave              │
│ (Day, Reason, Type)                 │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Status: PENDING                     │
│ (Awaiting Admin Approval)           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Admin Reviews & Approves            │
│ (Selects Substitute or Auto-assign) │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Substitute Assigned                 │
│ (All periods transferred)           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Notifications Sent:                 │
│ • Teacher: Approved ✓               │
│ • Substitute: Assigned ✓            │
│ • Students: Teacher Change ✓        │
└─────────────────────────────────────┘
```

### How to Use

#### Teacher Requests Leave
```bash
POST /api/leaves/request
Authorization: Bearer {token}
Content-Type: application/json

{
  "leave_date": "2026-05-30",
  "reason": "Medical appointment",
  "leave_type": "casual"
}

Success Response:
{
  "id": 1,
  "teacher_id": 3,
  "leave_date": "2026-05-30",
  "status": "pending",
  "created_at": "2026-05-25T10:30:00"
}
```

#### Admin Approves Leave
```bash
POST /api/leaves/{leave_request_id}/approve
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "substitute_teacher_id": 5,  // or null for auto-assignment
  "auto_adjust": true
}

Response:
{
  "id": 1,
  "status": "approved",
  "substitute_teacher_id": 5,
  "timetable_adjustments": {
    "original_slots": [...],
    "adjustments": [
      {
        "slot_id": 1,
        "old_teacher_id": 3,
        "new_teacher_id": 5
      }
    ]
  }
}
```

#### Mark Teacher Absent (Emergency)
```bash
POST /api/teachers/{teacher_id}/mark-absent
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "date": "2026-05-25"
}

Response:
{
  "success": true,
  "leave_request": {
    "id": 2,
    "status": "approved",
    "substitute_teacher_id": 5,
    ...
  }
}
```

#### Get Substitute Options
```bash
GET /api/leaves/{leave_request_id}/substitute-options
Authorization: Bearer {admin_token}

Response:
[
  {
    "id": 5,
    "name": "Priya Verma",
    "subjects": ["English", "Mathematics"],
    "load": 4
  },
  {
    "id": 7,
    "name": "Meera Desai",
    "subjects": ["History", "Geography"],
    "load": 3
  }
]
```

#### Backend Implementation (Complete ✅)
- **File**: `backend/leave_service.py`
- **Key Methods**:
  - `request_leave()` - Create leave request
  - `approve_leave()` - Approve with substitute
  - `_find_best_substitute()` - Smart substitute recommendation
  - `_adjust_timetable_for_leave()` - Auto-transfer periods
  - `mark_teacher_absent()` - Emergency marking

#### Frontend Component Example

```typescript
// src/components/LeaveRequest.tsx
import React, { useState } from 'react';
import { api } from '../api';

export const LeaveRequest: React.FC = () => {
  const [formData, setFormData] = useState({
    leave_date: '',
    reason: '',
    leave_type: 'casual'
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.leave.request(
        formData.leave_date,
        formData.reason,
        formData.leave_type
      );
      setSuccess(true);
      setFormData({ leave_date: '', reason: '', leave_type: 'casual' });
    } catch (error) {
      console.error('Failed to request leave:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="leave-form">
      <div className="form-group">
        <label>Leave Date</label>
        <input
          type="date"
          value={formData.leave_date}
          onChange={(e) => setFormData({...formData, leave_date: e.target.value})}
          required
        />
      </div>

      <div className="form-group">
        <label>Reason</label>
        <textarea
          value={formData.reason}
          onChange={(e) => setFormData({...formData, reason: e.target.value})}
          placeholder="Explain your leave request..."
          required
        />
      </div>

      <div className="form-group">
        <label>Leave Type</label>
        <select
          value={formData.leave_type}
          onChange={(e) => setFormData({...formData, leave_type: e.target.value})}
        >
          <option value="casual">Casual</option>
          <option value="sick">Sick</option>
          <option value="emergency">Emergency</option>
          <option value="other">Other</option>
        </select>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? 'Submitting...' : 'Request Leave'}
      </button>

      {success && <p className="success">Leave request submitted!</p>}
    </form>
  );
};
```

---

## 3. 🔔 Real-time Notifications

### Overview
Comprehensive notification system for all major events:
- Timetable generation/updates
- Leave approvals/rejections
- Teacher substitutions
- Class timing changes

### Events Triggering Notifications

| Event | Triggered When | Recipients |
|-------|----------------|-----------|
| **Timetable Generated** | Admin creates timetable | Admin, Principal |
| **Timetable Updated** | Timetable is modified | All staff |
| **Leave Approved** | Admin approves teacher leave | Teacher, Substitute, Students |
| **Leave Rejected** | Admin rejects leave | Teacher |
| **Teacher Substituted** | Substitute assigned | Students of affected batch |
| **Teacher Absent** | Emergency absence marked | All staff, students |
| **Timing Changed** | Class time rescheduled | Teachers, students |

### How to Use

#### Get Notifications
```bash
GET /api/notifications?limit=20&unread_only=false
Authorization: Bearer {token}

Response:
[
  {
    "id": 1,
    "title": "Leave Approved",
    "message": "Your leave for 29 May has been approved",
    "notification_type": "leave_approved",
    "is_read": false,
    "action_url": "/teacher/leaves/1",
    "created_at": "2026-05-25T10:30:00"
  }
]
```

#### Get Unread Count
```bash
GET /api/notifications/unread-count
Authorization: Bearer {token}

Response:
{
  "unread_count": 5
}
```

#### Mark as Read
```bash
POST /api/notifications/{notification_id}/mark-read
Authorization: Bearer {token}

Response:
{
  "id": 1,
  "is_read": true,
  ...
}
```

#### Delete Notification
```bash
DELETE /api/notifications/{notification_id}
Authorization: Bearer {token}
```

#### Frontend Hook Example

```typescript
// src/hooks/useNotifications.ts
import { useState, useEffect } from 'react';
import { api } from '../api';

export const useNotifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  // Fetch notifications periodically
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const [notifs, { unread_count }] = await Promise.all([
          api.notifications.getAll({ limit: 20 }),
          api.notifications.getUnreadCount()
        ]);
        setNotifications(notifs);
        setUnreadCount(unread_count);
      } catch (error) {
        console.error('Failed to fetch notifications:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchNotifications();

    // Poll every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const markAsRead = async (id: number) => {
    try {
      await api.notifications.markRead(id);
      setNotifications(
        notifications.map(n => n.id === id ? {...n, is_read: true} : n)
      );
      setUnreadCount(Math.max(0, unreadCount - 1));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const deleteNotification = async (id: number) => {
    try {
      await api.notifications.delete(id);
      setNotifications(notifications.filter(n => n.id !== id));
    } catch (error) {
      console.error('Failed to delete notification:', error);
    }
  };

  return {
    notifications,
    unreadCount,
    loading,
    markAsRead,
    deleteNotification
  };
};

// Usage in component
export const NotificationCenter: React.FC = () => {
  const { notifications, unreadCount, markAsRead } = useNotifications();

  return (
    <div className="notification-center">
      <h3>Notifications ({unreadCount} unread)</h3>
      {notifications.map(notif => (
        <div
          key={notif.id}
          className={`notification ${notif.is_read ? 'read' : 'unread'}`}
          onClick={() => !notif.is_read && markAsRead(notif.id)}
        >
          <h4>{notif.title}</h4>
          <p>{notif.message}</p>
          <small>{new Date(notif.created_at).toLocaleString()}</small>
        </div>
      ))}
    </div>
  );
};
```

---

## 📦 Installation & Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Database Migrations
```bash
# First time - run seed
python seed.py

# Or use API endpoint
curl -X POST http://localhost:5000/api/seed \
  -H "Authorization: Bearer {admin_token}"
```

### 3. Start Backend
```bash
export FLASK_ENV=development
export DATABASE_URL="sqlite:///timetable.db"
python -m flask run --port=5000
```

### 4. Test Features
```bash
# Test PDF Export
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer {token}" \
  -o timetable.pdf

# Test Leave Request
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer {teacher_token}" \
  -H "Content-Type: application/json" \
  -d '{"leave_date":"2026-05-30","reason":"Sick","leave_type":"sick"}'

# Test Notifications
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer {token}"
```

---

## 🧪 Test Scenarios

### Scenario 1: Request and Approve Leave
```bash
# 1. Teacher requests leave
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"priya.verma@school.edu","password":"teacher123"}' \
  | jq -r '.token')

curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_date":"2026-05-30","reason":"Medical","leave_type":"sick"}'

# 2. Admin approves leave
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"admin123"}' \
  | jq -r '.token')

curl -X POST http://localhost:5000/api/leaves/1/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"auto_adjust":true}'

# 3. Check notifications
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 2: Emergency Teacher Absence
```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"principal@school.edu","password":"principal123"}' \
  | jq -r '.token')

curl -X POST http://localhost:5000/api/teachers/3/mark-absent \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-05-25"}'
```

### Scenario 3: Download Timetable PDF
```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"principal@school.edu","password":"principal123"}' \
  | jq -r '.token')

curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o timetable_batch.pdf

echo "PDF saved as timetable_batch.pdf"
```

---

## ✅ Deployment Checklist

- [ ] Update `requirements.txt` with new packages (reportlab, WeasyPrint, Pillow)
- [ ] Run database migrations or seed script
- [ ] Test PDF export with correct school name
- [ ] Test leave approval workflow with substitute assignment
- [ ] Verify notifications are created for all events
- [ ] Load test with 10+ concurrent users
- [ ] Test on different devices (desktop, tablet, mobile)
- [ ] Configure CORS for frontend domain
- [ ] Set up log aggregation for error tracking
- [ ] Document any custom school configurations
- [ ] Train staff on new features

---

## 🐛 Troubleshooting

### PDF Export Not Working
```bash
# Check dependencies
python -c "import reportlab, weasyprint; print('OK')"

# Check file permissions
ls -la /Users/aarohi_sharma/cpp\ project/timetable.db

# Check Flask logs for errors
python -m flask run --port=5000  # Look for error messages
```

### Leave Not Being Substituted
```bash
# Check available substitutes
curl http://localhost:5000/api/leaves/1/substitute-options \
  -H "Authorization: Bearer $TOKEN"

# Verify teacher assignments
curl http://localhost:5000/api/admin/teachers \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {name, subject_ids, assigned_batch_ids}'
```

### Notifications Not Appearing
```bash
# Check notification count
curl http://localhost:5000/api/notifications/unread-count \
  -H "Authorization: Bearer $TOKEN"

# Check database
sqlite3 timetable.db "SELECT COUNT(*) FROM notifications;"
```

---

## 📚 Related Documentation

- **API Documentation**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Models**: [models.py](models.py)
- **Routes**: [routes.py](routes.py)
- **PDF Utilities**: [pdf_utils.py](pdf_utils.py)
- **Leave Service**: [leave_service.py](leave_service.py)

---

**Last Updated**: 25 May 2026  
**Version**: 1.0  
**Features Complete**: ✅ PDF Export  |  ✅ Leave Management  |  ✅ Notifications
