# API Reference

REST API for the School Management & Timetable System.

- **Base URL**: `http://localhost:5000/api`
- **Auth**: JWT bearer token in the `Authorization: Bearer <token>` header.
- **Content-Type**: `application/json` for all `POST` / `PUT` bodies.

---

## Authentication

### Login
```http
POST /api/auth/login
```
```json
{ "email": "admin@school.edu", "password": "admin123" }
```
Response:
```json
{
  "token": "eyJhbGciOi...",
  "user": { "id": 1, "name": "Admin", "email": "admin@school.edu", "role": "admin" }
}
```

### Current User
```http
GET /api/auth/me
Authorization: Bearer <token>
```

### Logout
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

---

## Health & Stats

| Method | Path             | Description                       |
| ------ | ---------------- | --------------------------------- |
| GET    | `/api/health`    | Liveness probe (`{"status":"ok"}`)|
| GET    | `/api/stats`     | High-level counts (users, batches)|
| POST   | `/api/seed`      | Re-run minimal seed (admin only)  |

---

## School Configuration

| Method | Path                           | Role          |
| ------ | ------------------------------ | ------------- |
| GET    | `/api/admin/school-config`     | admin/principal|
| POST   | `/api/admin/school-config`     | admin         |

Body for `POST`:
```json
{
  "school_name": "...",
  "periods_per_day": 8,
  "period_duration_minutes": 45,
  "start_time": "08:00",
  "lunch_after_period": 4
}
```

---

## Teachers

| Method | Path                                  | Role        |
| ------ | ------------------------------------- | ----------- |
| GET    | `/api/admin/teachers`                 | admin       |
| POST   | `/api/admin/teachers`                 | admin       |
| GET    | `/api/admin/teachers/{teacher_id}`    | admin       |
| PUT    | `/api/admin/teachers/{teacher_id}`    | admin       |
| DELETE | `/api/admin/teachers/{teacher_id}`    | admin       |

---

## Students

| Method | Path             | Role               |
| ------ | ---------------- | ------------------ |
| GET    | `/api/students`  | admin/principal/coordinator |

Query parameters: `class`, `section`, `search`.

---

## Batches (Classes)

| Method | Path                              | Role  |
| ------ | --------------------------------- | ----- |
| GET    | `/api/admin/batches`              | admin |
| POST   | `/api/admin/batches`              | admin |
| GET    | `/api/admin/batches/{batch_id}`   | admin |
| PUT    | `/api/admin/batches/{batch_id}`   | admin |
| DELETE | `/api/admin/batches/{batch_id}`   | admin |

---

## Subjects

| Method | Path                                  | Role  |
| ------ | ------------------------------------- | ----- |
| GET    | `/api/admin/subjects`                 | admin |
| POST   | `/api/admin/subjects`                 | admin |
| GET    | `/api/admin/subjects/{subject_id}`    | admin |
| PUT    | `/api/admin/subjects/{subject_id}`    | admin |
| DELETE | `/api/admin/subjects/{subject_id}`    | admin |

---

## Timetable

### Generate
```http
POST /api/timetable/generate
Authorization: Bearer <admin token>
```
Body (optional overrides):
```json
{ "regenerate": true, "batch_ids": [1, 2] }
```

### List / Get
| Method | Path                                  | Role   |
| ------ | ------------------------------------- | ------ |
| GET    | `/api/timetable`                      | any    |
| GET    | `/api/timetable/{timetable_id}`       | any    |
| POST   | `/api/timetable/{timetable_id}/publish` | admin |

### Validation & Conflicts
| Method | Path                                                       |
| ------ | ---------------------------------------------------------- |
| GET    | `/api/timetable/{timetable_id}/validate`                   |
| GET    | `/api/timetable/{timetable_id}/conflicts/summary`          |
| GET    | `/api/timetable/{timetable_id}/conflicts/by-type`          |
| GET    | `/api/timetable/batch/{batch_id}`                          |

Conflict types returned:
- `teacher_double_booked` (ERROR)
- `batch_double_booked` (ERROR)
- `subject_gap` (WARNING)
- `uneven_distribution` (WARNING)

### Personal Timetables
| Method | Path                          | Role    |
| ------ | ----------------------------- | ------- |
| GET    | `/api/teacher/my-timetable`   | teacher |
| GET    | `/api/student/my-timetable`   | student |

---

## PDF Export

| Method | Path                                                    | Role             |
| ------ | ------------------------------------------------------- | ---------------- |
| GET    | `/api/export/timetable/batch/{timetable_id}`            | admin/principal  |
| GET    | `/api/export/timetable/teacher/{timetable_id}`          | admin/principal/teacher |

Optional query: `?school_name=My%20School` to customize the header.

Example:
```bash
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o class_7b.pdf
```

---

## Leave Management

### Request leave (teacher)
```http
POST /api/leaves/request
```
```json
{
  "leave_date": "2026-06-03",
  "reason": "Medical appointment",
  "leave_type": "casual"   // sick | casual | emergency | other
}
```

### List / Get
| Method | Path                                  | Notes                                |
| ------ | ------------------------------------- | ------------------------------------ |
| GET    | `/api/leaves`                         | Filter: `status`, `from_date`, `to_date`, `leave_type`. Teachers only see their own. |
| GET    | `/api/leaves/{leave_request_id}`      |                                      |

### Approve / Reject (admin or principal)
```http
POST /api/leaves/{leave_request_id}/approve
```
```json
{ "substitute_teacher_id": 5, "auto_adjust": true }
```

```http
POST /api/leaves/{leave_request_id}/reject
```
```json
{ "reason": "Insufficient notice" }
```

### Substitute Finder
```http
GET /api/leaves/{leave_request_id}/substitute-options
```
Returns teachers who:
- Teach the same subject(s).
- Have no other classes that day.
- Are not on leave.

### Mark Teacher Absent (admin)
```http
POST /api/teachers/{teacher_id}/mark-absent
```
```json
{ "date": "2026-06-03", "auto_assign_substitute": true }
```

---

## Notifications

| Method | Path                                                  | Description                    |
| ------ | ----------------------------------------------------- | ------------------------------ |
| GET    | `/api/notifications`                                  | List current user's notifications |
| GET    | `/api/notifications/unread-count`                     | Returns `{ "count": N }`       |
| POST   | `/api/notifications/{notification_id}/mark-read`      | Mark a single notification read|
| POST   | `/api/notifications/mark-all-read`                    | Mark all read                  |
| DELETE | `/api/notifications/{notification_id}`                | Delete a notification          |

Notifications are auto-created on:
- Timetable generated / published
- Leave approved / rejected
- Teacher substituted
- Classroom or schedule changes

---

## Dashboards & Analytics

| Method | Path                                | Role       |
| ------ | ----------------------------------- | ---------- |
| GET    | `/api/principal/dashboard`          | principal  |
| GET    | `/api/analytics/{timetable_id}`     | admin/principal |
| GET    | `/api/plans`                        | admin      |
| GET    | `/api/plans/{timetable_id}`         | admin      |

---

## Roles & Access Matrix

| Role        | Can do                                                              |
| ----------- | ------------------------------------------------------------------- |
| admin       | Everything (config, CRUD, generate, publish, approve leaves)        |
| principal   | View all, approve/reject leaves, dashboard, publish timetables      |
| coordinator | View students/teachers in their section                             |
| teacher     | View own timetable, request leave, view own notifications, export own PDF |
| student     | View own timetable                                                  |

---

## Quick cURL Recipes

```bash
# 1. Get an admin token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"admin123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. Generate a timetable
curl -X POST http://localhost:5000/api/timetable/generate \
  -H "Authorization: Bearer $TOKEN"

# 3. Check for conflicts
curl http://localhost:5000/api/timetable/1/conflicts/summary \
  -H "Authorization: Bearer $TOKEN"

# 4. Export a PDF
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" -o timetable.pdf

# 5. Approve a leave with a substitute
curl -X POST http://localhost:5000/api/leaves/1/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"substitute_teacher_id":5,"auto_adjust":true}'
```

---

## Error Responses

All errors are JSON with a consistent shape:

```json
{ "error": "Unauthorized", "message": "Token is missing or invalid" }
```

| Status | Meaning                                      |
| ------ | -------------------------------------------- |
| 400    | Bad request / validation error               |
| 401    | Missing or invalid JWT                       |
| 403    | Authenticated but role not permitted         |
| 404    | Resource not found                           |
| 409    | Conflict (e.g. duplicate leave for the day)  |
| 500    | Server error                                 |

For installation and account credentials see [`SETUP.md`](./SETUP.md). For architecture see [`ABOUT.md`](./ABOUT.md).
