# 🚀 Quick Reference - New Features API

## Base URL
`http://localhost:5000/api`

---

## 📄 PDF Export Endpoints

```bash
 # Batch-wise timetable (one grade per page)
GET /export/timetable/batch/{timetable_id}
  Authorization: Bearer {token}
  Roles: admin, principal
  Response: PDF file

# Teacher-wise timetable (one teacher per page)
GET /export/timetable/teacher/{timetable_id}
  Authorization: Bearer {token}
  Roles: admin, principal, teacher
  Response: PDF file

# Download example
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o timetable.pdf
```

---

## 🏥 Leave Management Endpoints

```bash
# Request leave (Teacher)
POST /leaves/request
  Body: {
    "leave_date": "2026-05-30",
    "reason": "Medical appointment",
    "leave_type": "sick|casual|emergency"
  }
  → Returns: LeaveRequest object

# Get leave requests
GET /leaves
  Params: ?status=pending&from_date=2026-05-01&to_date=2026-05-31
  → Returns: List of LeaveRequest objects

# Get single leave request
GET /leaves/{id}
  → Returns: LeaveRequest object

# Approve leave (Admin/Principal)
POST /leaves/{id}/approve
  Body: {
    "substitute_teacher_id": 5,  # optional
    "auto_adjust": true
  }
  → Returns: Approved LeaveRequest with adjustments

# Reject leave (Admin/Principal)
POST /leaves/{id}/reject
  Body: {
    "rejection_reason": "Cannot approve during exams"
  }
  → Returns: Rejected LeaveRequest

# Get substitute options (Admin/Principal)
GET /leaves/{id}/substitute-options
  → Returns: List of available teachers

# Mark teacher absent immediately (Admin/Principal)
POST /teachers/{teacher_id}/mark-absent
  Body: {
    "date": "2026-05-25"
  }
  → Returns: LeaveRequest with auto-assigned substitute

# Examples
# Request leave
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_date":"2026-05-30","reason":"Sick","leave_type":"sick"}'

# Approve leave
curl -X POST http://localhost:5000/api/leaves/1/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"auto_adjust":true}'

# Mark absent
curl -X POST http://localhost:5000/api/teachers/3/mark-absent \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-05-25"}'
```

---

## 🔔 Notification Endpoints

```bash
# Get all notifications
GET /notifications
  Params: ?limit=20&unread_only=false
  → Returns: List of Notification objects

# Get unread count
GET /notifications/unread-count
  → Returns: { "unread_count": 5 }

# Mark single notification as read
POST /notifications/{id}/mark-read
  → Returns: Updated Notification

# Mark all notifications as read
POST /notifications/mark-all-read
  → Returns: { "message": "All marked as read" }

# Delete notification
DELETE /notifications/{id}
  → Returns: { "message": "Deleted" }

# Examples
# Get notifications
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer $TOKEN"

# Mark as read
curl -X POST http://localhost:5000/api/notifications/1/mark-read \
  -H "Authorization: Bearer $TOKEN"

# Get unread count
curl http://localhost:5000/api/notifications/unread-count \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Data Models

### LeaveRequest
```json
{
  "id": 1,
  "teacher_id": 3,
  "leave_date": "2026-05-30",
  "reason": "Medical appointment",
  "leave_type": "sick|casual|emergency|other",
  "status": "pending|approved|rejected",
  "approved_by": 1,
  "substitute_teacher_id": 5,
  "rejection_reason": null,
  "timetable_adjustments": {
    "original_slots": [...],
    "adjustments": [...]
  },
  "created_at": "2026-05-25T10:30:00"
}
```

### Notification
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Leave Approved",
  "message": "Your leave for 29 May has been approved",
  "notification_type": "leave_approved|teacher_substituted|...",
  "related_id": 2,
  "is_read": false,
  "action_url": "/teacher/leaves/2",
  "created_at": "2026-05-25T10:30:00",
  "expires_at": null
}
```

---

## 🔐 Authentication

```bash
# Get JWT token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"principal@school.edu","password":"principal123"}'

# Response:
# {
#   "token": "eyJhbGc...",
#   "user": {...}
# }

# Use token
Authorization: Bearer {token}

# Test accounts (from seed.py)
admin@school.edu / admin123
principal@school.edu / principal123
priya.verma@school.edu / teacher123
student9A1@school.edu / student123
```

---

## ✨ Notification Types

| Type | Triggered By | Recipients |
|------|------------|-----------|
| `timetable_generated` | Timetable creation | Admin, Principal |
| `timetable_updated` | Timetable modification | All staff |
| `leave_approved` | Admin approves leave | Teacher, Substitute, Students |
| `leave_rejected` | Admin rejects leave | Teacher |
| `teacher_substituted` | Substitute assigned | Affected students |
| `teacher_absent` | Emergency absence | All staff, students |

---

## 🧪 Test Scenarios (Copy & Paste Ready)

### Scenario 1: Request & Approve Leave
```bash
# 1. Get teacher token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"priya.verma@school.edu","password":"teacher123"}' \
  | jq -r '.token')

# 2. Request leave
LEAVE_ID=$(curl -s -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_date":"2026-05-30","reason":"Medical","leave_type":"sick"}' \
  | jq -r '.id')

echo "Leave request ID: $LEAVE_ID"

# 3. Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"admin123"}' \
  | jq -r '.token')

# 4. Approve leave
curl -X POST http://localhost:5000/api/leaves/$LEAVE_ID/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"auto_adjust":true}'

# 5. Check notifications
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### Scenario 2: Download Timetable PDF
```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"principal@school.edu","password":"principal123"}' \
  | jq -r '.token')

# Batch-wise PDF
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o batch_timetable.pdf

# Teacher-wise PDF
curl http://localhost:5000/api/export/timetable/teacher/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o teacher_timetable.pdf

echo "PDFs downloaded successfully"
```

### Scenario 3: Emergency Teacher Absence
```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"principal@school.edu","password":"principal123"}' \
  | jq -r '.token')

curl -X POST http://localhost:5000/api/teachers/3/mark-absent \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-05-25"}' | jq '.leave_request'
```

---

## 🚀 Frontend Integration Snippet

```typescript
// src/api.ts
const api = {
  // PDF Export
  export: {
    batch: (id: number) => 
      axiosInstance.get(`/export/timetable/batch/${id}`, { responseType: 'blob' }),
    teacher: (id: number) => 
      axiosInstance.get(`/export/timetable/teacher/${id}`, { responseType: 'blob' })
  },

  // Leave Management
  leave: {
    request: (date: string, reason: string, type: string) =>
      axiosInstance.post('/leaves/request', { leave_date: date, reason, leave_type: type }),
    getAll: (filters?: any) => 
      axiosInstance.get('/leaves', { params: filters }),
    approve: (id: number) =>
      axiosInstance.post(`/leaves/${id}/approve`, { auto_adjust: true }),
    reject: (id: number, reason: string) =>
      axiosInstance.post(`/leaves/${id}/reject`, { rejection_reason: reason }),
    getSubstitutes: (id: number) =>
      axiosInstance.get(`/leaves/${id}/substitute-options`)
  },

  // Notifications
  notification: {
    getAll: (limit = 20) =>
      axiosInstance.get('/notifications', { params: { limit } }),
    getUnreadCount: () =>
      axiosInstance.get('/notifications/unread-count'),
    markRead: (id: number) =>
      axiosInstance.post(`/notifications/${id}/mark-read`),
    delete: (id: number) =>
      axiosInstance.delete(`/notifications/${id}`)
  }
};

// Usage
// Download PDF
const downloadPDF = async (timetableId: number, type: 'batch' | 'teacher') => {
  const response = await api.export[type](timetableId);
  const url = URL.createObjectURL(response);
  const link = document.createElement('a');
  link.href = url;
  link.download = `timetable_${type}.pdf`;
  link.click();
};

// Request leave
await api.leave.request('2026-05-30', 'Medical', 'sick');

// Get unread notifications
const { data } = await api.notification.getUnreadCount();
console.log(`You have ${data.unread_count} unread notifications`);
```

---

## 🔧 Common Issues

| Issue | Solution |
|-------|----------|
| PDF export returns 401 | Get valid JWT token: `POST /auth/login` |
| PDF shows "Not found" | Verify timetable_id exists: `GET /plans` |
| Leave approval fails | Check teacher has no conflicting leave already |
| No substitutes available | Teacher may be fully booked, try manual selection |
| Notifications not appearing | Poll every 30 seconds or implement WebSocket |

---

## 📝 Response Codes

```
200 OK              - Success
201 Created         - Resource created
400 Bad Request     - Invalid data
401 Unauthorized    - Missing/invalid token
403 Forbidden       - Role not allowed
404 Not Found       - Resource doesn't exist
500 Internal Error  - Server error
```

---

## ⚡ Performance Tips

- Cache notification count in frontend state
- Paginate notifications (use `?limit=10`)
- Pre-fetch substitute list before showing modal
- Queue PDF exports for large datasets
- Batch mark multiple notifications as read

---

## 📚 Documentation Links

- [Full API Docs](API_DOCUMENTATION.md)
- [Features Guide](FEATURES_GUIDE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Troubleshooting Auth](TROUBLESHOOTING_401.md)

---

**Quick Reference Card - Save this for daily use!**  
**Last Updated: 25 May 2026**
