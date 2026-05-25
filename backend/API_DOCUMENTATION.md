# School Timetable API Documentation

## Overview
Complete REST API for school timetable scheduling with leave management and real-time notifications.

---

## Base URL
- **Development**: `http://localhost:5000/api`
- **Environment Variable**: `REACT_APP_API_URL`

---

## 🔐 Authentication

### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "principal@school.edu",
  "password": "principal123"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "name": "Dr. Rajesh Sharma",
    "email": "principal@school.edu",
    "role": "principal",
    "batch_id": null
  }
}
```

### Get Current User
```bash
GET /api/auth/me
Authorization: Bearer {token}

Response:
{
  "id": 1,
  "name": "Dr. Rajesh Sharma",
  "email": "principal@school.edu",
  "role": "principal"
}
```

---

## 📊 PDF Export

### Export Timetable (Batch-wise)
```bash
GET /api/export/timetable/batch/{timetable_id}
Authorization: Bearer {token}
Role: admin, principal

Query Parameters:
  - school_name (optional): Custom school name for header

Response: PDF file download
Filename: timetable_batch_{timetable_id}.pdf
```

**Features:**
- ✅ A4 landscape layout
- ✅ School header with name and date
- ✅ One batch per page
- ✅ Period-wise timetable grid
- ✅ Teacher and subject names
- ✅ Lunch breaks clearly marked

### Export Timetable (Teacher-wise)
```bash
GET /api/export/timetable/teacher/{timetable_id}
Authorization: Bearer {token}
Role: admin, principal, teacher

Response: PDF file download
Filename: timetable_teacher_{timetable_id}.pdf
```

**Features:**
- ✅ One teacher per page
- ✅ Shows all assigned batches/periods
- ✅ Professional A4 layout
- ✅ Color-coded headers

---

## 🏥 Leave Management

### Request Leave
```bash
POST /api/leaves/request
Authorization: Bearer {token}
Role: teacher
Content-Type: application/json

{
  "leave_date": "2026-05-30",
  "reason": "Medical appointment",
  "leave_type": "casual"  // "sick", "casual", "emergency", "other"
}

Response (201 Created):
{
  "id": 1,
  "teacher_id": 3,
  "leave_date": "2026-05-30",
  "reason": "Medical appointment",
  "leave_type": "casual",
  "status": "pending",
  "approved_by": null,
  "substitute_teacher_id": null,
  "created_at": "2026-05-25T10:30:00"
}
```

### Get All Leave Requests
```bash
GET /api/leaves
Authorization: Bearer {token}

Query Parameters:
  - status: "pending" | "approved" | "rejected"
  - from_date: "2026-05-01"
  - to_date: "2026-05-31"
  - leave_type: "sick" | "casual" | "emergency"

Response (200 OK):
[
  {
    "id": 1,
    "teacher_id": 3,
    "leave_date": "2026-05-30",
    "status": "pending",
    ...
  }
]

Note: Teachers only see their own leaves
```

### Get Single Leave Request
```bash
GET /api/leaves/{leave_request_id}
Authorization: Bearer {token}

Response (200 OK):
{
  "id": 1,
  "teacher_id": 3,
  "leave_date": "2026-05-30",
  "reason": "Medical appointment",
  "leave_type": "casual",
  "status": "pending",
  "approved_by": null,
  "substitute_teacher_id": null,
  "timetable_adjustments": {}
}
```

### Approve Leave Request
```bash
POST /api/leaves/{leave_request_id}/approve
Authorization: Bearer {token}
Role: admin, principal
Content-Type: application/json

{
  "substitute_teacher_id": 5,  // optional, auto-assigned if not provided
  "auto_adjust": true          // automatically adjust timetable
}

Response (200 OK):
{
  "id": 1,
  "teacher_id": 3,
  "leave_date": "2026-05-30",
  "status": "approved",
  "substitute_teacher_id": 5,
  "timetable_adjustments": {
    "original_slots": [
      {
        "slot_id": 1,
        "day": "Monday",
        "period": 2,
        "batch_id": 1,
        "subject_id": 3,
        "teacher_id": 3
      }
    ],
    "adjustments": [
      {
        "slot_id": 1,
        "day": "Monday",
        "period": 2,
        "batch_id": 1,
        "subject_id": 3,
        "old_teacher_id": 3,
        "new_teacher_id": 5
      }
    ]
  }
}
```

**Processing:**
1. ✅ Validates substitute availability (no conflicts)
2. ✅ Auto-finds best substitute if not provided
3. ✅ Transfers all periods to substitute
4. ✅ Creates notifications for:
   - Requesting teacher
   - Substitute teacher
   - All affected students/batches
5. ✅ Returns adjusted timetable

### Reject Leave Request
```bash
POST /api/leaves/{leave_request_id}/reject
Authorization: Bearer {token}
Role: admin, principal
Content-Type: application/json

{
  "rejection_reason": "Cannot approve during exam period"
}

Response (200 OK):
{
  "id": 1,
  "status": "rejected",
  "rejection_reason": "Cannot approve during exam period"
}
```

### Get Substitute Options
```bash
GET /api/leaves/{leave_request_id}/substitute-options
Authorization: Bearer {token}
Role: admin, principal

Response (200 OK):
[
  {
    "id": 5,
    "name": "Priya Verma",
    "subjects": ["English", "Mathematics"],
    "load": 4  // current class count
  },
  {
    "id": 7,
    "name": "Meera Desai",
    "subjects": ["History", "Geography"],
    "load": 3
  }
]

Note: Only available teachers shown
```

### Mark Teacher Absent (Immediate)
```bash
POST /api/teachers/{teacher_id}/mark-absent
Authorization: Bearer {token}
Role: admin, principal
Content-Type: application/json

{
  "date": "2026-05-25"
}

Response (200 OK):
{
  "success": true,
  "leave_request": {
    "id": 2,
    "teacher_id": 3,
    "leave_date": "2026-05-25",
    "reason": "Marked absent by administrator",
    "leave_type": "unplanned",
    "status": "approved",
    "substitute_teacher_id": 5,
    "timetable_adjustments": { ... }
  }
}
```

**Automatic Actions:**
1. ✅ Creates leave request immediately
2. ✅ Auto-finds best substitute
3. ✅ Transfers all periods to substitute
4. ✅ Notifies all affected parties
5. ✅ Updates live timetable

---

## 🔔 Notifications

### Get User Notifications
```bash
GET /api/notifications
Authorization: Bearer {token}

Query Parameters:
  - limit: 20 (default)
  - unread_only: true | false (default: false)

Response (200 OK):
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Timetable Generated",
    "message": "Your timetable has been generated successfully",
    "notification_type": "timetable_generated",
    "related_id": 5,
    "is_read": false,
    "action_url": "/admin/timetable/5",
    "created_at": "2026-05-25T10:30:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "title": "Teacher Substituted",
    "message": "Priya Verma will substitute for Rajesh Kumar on Monday",
    "notification_type": "teacher_substituted",
    "related_id": 1,
    "is_read": false,
    "action_url": "/admin/leaves/1",
    "created_at": "2026-05-25T11:00:00"
  }
]
```

### Get Unread Count
```bash
GET /api/notifications/unread-count
Authorization: Bearer {token}

Response (200 OK):
{
  "unread_count": 5
}
```

### Mark Notification as Read
```bash
POST /api/notifications/{notification_id}/mark-read
Authorization: Bearer {token}

Response (200 OK):
{
  "id": 1,
  "is_read": true,
  ...
}
```

### Mark All Notifications as Read
```bash
POST /api/notifications/mark-all-read
Authorization: Bearer {token}

Response (200 OK):
{
  "message": "All notifications marked as read"
}
```

### Delete Notification
```bash
DELETE /api/notifications/{notification_id}
Authorization: Bearer {token}

Response (200 OK):
{
  "message": "Notification deleted"
}
```

---

## 📋 Notification Types

| Type | Triggered by | Recipients |
|------|-------------|-----------|
| `timetable_generated` | Timetable creation | Admin, Principal |
| `timetable_updated` | Timetable modification | Admin, Principal, Teachers |
| `teacher_substituted` | Leave approval with substitute | Students, Batch members |
| `timing_changed` | Period/class reschedule | Affected teachers, students |
| `leave_request_pending` | Teacher requests leave | Admin, Principal |
| `leave_approved` | Admin approves leave | Teacher, Substitute, Students |
| `leave_rejected` | Admin rejects leave | Teacher |
| `teacher_absent` | Immediate absence marking | All staff, Students |

---

## 🔧 Implementation Examples

### React Frontend Integration

#### Request Leave (Teacher)
```typescript
// src/api.ts
const leaveAPI = {
  request: (leaveDate: string, reason: string, leaveType: string) =>
    axiosInstance.post('/leaves/request', {
      leave_date: leaveDate,
      reason,
      leave_type: leaveType
    }),

  getAll: (filters?: object) =>
    axiosInstance.get('/leaves', { params: filters }),

  approve: (id: number, substituteId?: number) =>
    axiosInstance.post(`/leaves/${id}/approve`, {
      substitute_teacher_id: substituteId,
      auto_adjust: true
    }),

  reject: (id: number, reason: string) =>
    axiosInstance.post(`/leaves/${id}/reject`, {
      rejection_reason: reason
    })
};
```

#### Download PDF
```typescript
// Download in browser
const downloadPDF = async (timetableId: number, type: 'batch' | 'teacher') => {
  const endpoint = `/export/timetable/${type}/${timetableId}`;
  const response = await axiosInstance.get(endpoint, {
    responseType: 'blob'
  });

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `timetable_${type}_${timetableId}.pdf`);
  document.body.appendChild(link);
  link.click();
};
```

#### Real-time Notifications
```typescript
// src/hooks/useNotifications.ts
const useNotifications = () => {
  const [notifications, setNotifications] = useState([]);

  // Poll every 30 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await axiosInstance.get('/notifications?limit=10');
      setNotifications(response.data);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const markAsRead = async (id: number) => {
    await axiosInstance.post(`/notifications/${id}/mark-read`);
  };

  return { notifications, markAsRead };
};
```

---

## ⚙️ Configuration

### School Header/Logo in PDF
```bash
# Add to Timetable on creation:
POST /api/timetables

{
  "name": "May 2026 Timetable",
  "school_name": "St. Xavier's School",
  "school_logo_path": "/static/logo.png"
}
```

---

## 🧪 Testing with cURL

### Create Leave Request
```bash
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_date": "2026-05-30",
    "reason": "Sick leave",
    "leave_type": "sick"
  }'
```

### Export Batch Timetable
```bash
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o timetable.pdf
```

### Get Notifications
```bash
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

---

## 🚀 Deployment Checklist

- [ ] Set `DATABASE_URL` environment variable
- [ ] Set `SECRET_KEY` for JWT signing
- [ ] Configure CORS origins in `config.py`
- [ ] Test authentication flow
- [ ] Verify PDF export with custom school name
- [ ] Test leave approval with substitute assignment
- [ ] Verify notifications are created for all events
- [ ] Load test with multiple concurrent users
- [ ] Set up log rotation for API logs

---

## 📚 Related Files

- **Models**: [backend/models.py](models.py)
- **Routes**: [backend/routes.py](routes.py)
- **PDF Utilities**: [backend/pdf_utils.py](pdf_utils.py)
- **Leave Service**: [backend/leave_service.py](leave_service.py)
- **Database**: `timetable.db` (SQLite)

---

**Last Updated**: 25 May 2026
**API Version**: 1.0
