# ✅ Testing Checklist - Features & Data Validation

## 📋 Pre-Testing Setup

- [ ] Run `python backend/seed_realistic.py` 
- [ ] Start backend: `flask run --port=5000`
- [ ] Start frontend: `npm start` (in frontend folder)
- [ ] Database has 2,800 students: `sqlite3 timetable.db "SELECT COUNT(*) FROM students;"`

---

## 🧪 **Test 1: Database & Data Integrity**

### Check Student Data Loaded
```bash
# Open new terminal
sqlite3 timetable.db

# Inside SQLite, run these:
SELECT COUNT(*) FROM students;
# Expected: 2800

SELECT class_grade, COUNT(*) as count FROM students 
GROUP BY class_grade ORDER BY class_grade;
# Shows distribution across all classes

SELECT name, COUNT(*) FROM teachers GROUP BY name;
# Should show 75 teachers

SELECT COUNT(*) FROM coordinators;
# Should show: 5

SELECT COUNT(*) FROM houses;
# Should show: 4
```

**✅ PASS**: If all counts match above  
**❌ FAIL**: If counts are 0 or wrong

---

## Interface & Navigation

### Frontend Login
- [ ] Open http://localhost:3000
- [ ] See login page
- [ ] Enter: admin@school.edu / admin123
- [ ] Click "Login"
- [ ] Should redirect to Dashboard (NOT 401 error)
- [ ] Can navigate between pages

**✅ PASS**: Dashboard loads, no 401 errors  
**❌ FAIL**: See "401 Unauthorized" or blank page

---

## 🧪 **Test 2: PDF Export Feature**

### Get Admin Token (Terminal)
```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@school.edu","password":"admin123"}' \
  | jq -r '.access_token')

echo $TOKEN
# Should print a long string like: eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Test Batch Timetable Export
```bash
# Export first class timetable as PDF
curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o ~/Downloads/class_1_timetable.pdf

# Check file was created
ls -lh ~/Downloads/class_1_timetable.pdf
# Should show file size ~100-200 KB
```

### Verify PDF Quality
- [ ] File size is 100-200 KB (not 0 bytes)
- [ ] Can open the PDF (`open ~/Downloads/class_1_timetable.pdf`)
- [ ] PDF shows:
  - [ ] School name in header
  - [ ] "Class 1A" or similar
  - [ ] Timetable grid (days × periods)
  - [ ] All students listed
  - [ ] Professional formatting
  - [ ] A4 landscape layout

### Test Teacher Timetable Export
```bash
# Export teacher 1's timetable
curl http://localhost:5000/api/export/timetable/teacher/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o ~/Downloads/teacher_1_timetable.pdf

# Verify it has:
# - Teacher's name
# - All assigned classes
# - All periods
# - Professional formatting
```

**✅ PASS**: PDFs generate in < 5 seconds, look professional  
**❌ FAIL**: Error, blank PDF, or exceeds 5 seconds

---

## 🧪 **Test 3: Leave Management Workflow**

### A. Teacher Requests Leave
```bash
# Get teacher token
TEACHER_TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"priya.sharma@school.edu","password":"teacher123"}' \
  | jq -r '.access_token')

# Teacher requests leave
curl -X POST http://localhost:5000/api/leaves/request \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leave_date": "2024-06-03",
    "reason": "Medical appointment",
    "leave_type": "Medical"
  }'

# Should return:
# {
#   "success": true,
#   "leave_request_id": 1,
#   "message": "Leave request submitted successfully"
# }
```

- [ ] Get response with `leave_request_id`
- [ ] Status code 200 (not 400/401)

### B. Admin Views All Leave Requests
```bash
# Admin gets all leave requests
curl http://localhost:5000/api/leaves \
  -H "Authorization: Bearer $TOKEN"

# Should list all leave requests with status (PENDING, APPROVED, REJECTED)
```

- [ ] See the leave request you just created
- [ ] Status shows as "PENDING"

### C. Get Available Substitutes
```bash
# Using leave_request_id from above (let's say it's 1)
curl http://localhost:5000/api/leaves/1/substitute-options \
  -H "Authorization: Bearer $TOKEN"

# Returns ranked list of substitutes:
# {
#   "available_substitutes": [
#     {
#       "id": 3,
#       "name": "Rajesh Kumar",
#       "available_score": 0.95,
#       "reason": "Same subject, no conflict"
#     }
#   ]
# }
```

- [ ] Get list of substitute teachers
- [ ] Each has a score (0.0-1.0)
- [ ] Highest score is best substitute

### D. Admin Approves Leave with Substitute
```bash
# Admin approves and assigns substitute (teacher ID 3)
curl -X POST http://localhost:5000/api/leaves/1/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "substitute_teacher_id": 3,
    "auto_adjust": true
  }'

# Returns:
# {
#   "success": true,
#   "message": "Leave approved successfully",
#   "timetable_adjustments": {
#     "original_slots_transferred": 4,
#     "substitute_assignments": [...]
#   }
# }
```

- [ ] Get success response
- [ ] Shows number of slots transferred
- [ ] Notifications created

### E. Verify Timetable Updated
```bash
# Export teacher's new timetable
# Should now show substitute teacher in the original teacher's classes
curl http://localhost:5000/api/export/timetable/teacher/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o ~/Downloads/teacher_updated.pdf

# Open PDF - should see classes reassigned to substitute
```

- [ ] PDF shows substitute teaching original teacher's classes

**✅ PASS**: Request → Approve → Substitute → Timetable Updated  
**❌ FAIL**: Error at any step or timetable not updated

---

## 🧪 **Test 4: Notification System**

### Get User's Notifications
```bash
# Teacher gets notifications (should have approval notification)
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Returns:
# [
#   {
#     "id": 1,
#     "title": "Leave Approved",
#     "message": "Your leave for 2024-06-03 has been approved",
#     "is_read": false,
#     "created_at": "2024-05-28T10:30:00"
#   }
# ]
```

- [ ] See notification about leave approval
- [ ] `is_read` is false

### Mark Notification as Read
```bash
# Mark notification as read
curl -X POST http://localhost:5000/api/notifications/1/mark-read \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Get notifications again - is_read should be true
curl http://localhost:5000/api/notifications \
  -H "Authorization: Bearer $TEACHER_TOKEN"
```

- [ ] Notification marked as read
- [ ] Can see read status changed

### Get Unread Count
```bash
# See how many unread notifications
curl http://localhost:5000/api/notifications/unread-count \
  -H "Authorization: Bearer $TEACHER_TOKEN"

# Returns: { "unread_count": 0 }
```

- [ ] Count is accurate

**✅ PASS**: Create → View → Mark Read workflow works  
**❌ FAIL**: Notifications not showing or can't update

---

## 🧪 **Test 5: Student & Teacher Data**

### List All Students
```bash
curl http://localhost:5000/api/students \
  -H "Authorization: Bearer $TOKEN" | jq '.[:3]'

# Should show first 3 students with:
# - student_id
# - admission_no
# - first_name, last_name
# - class_grade, section
# - roll_no
# - house_name
```

- [ ] Can list students
- [ ] Data looks realistic (realistic names, classes)
- [ ] All fields populated

### Filter Students by Class
```bash
# Get all students in class 7, section B
curl "http://localhost:5000/api/students?class=7&section=B" \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | .first_name'

# Should show ~30-40 students
```

- [ ] Get realistic number of students (20-40 per class)
- [ ] All have class_grade="7", section="B"

### Get All Teachers
```bash
curl http://localhost:5000/api/students \
  -H "Authorization: Bearer $TOKEN" | jq '.[:5]'

# Should show 75 total teachers with:
# - name
# - designation (NTT, PRT, TGT, PGT, Specialist)
# - subject(s)
# - assigned_batches
```

- [ ] Can list all teachers
- [ ] Count is 75
- [ ] Each has proper designation

### Get Coordinators
```bash
curl http://localhost:5000/api/coordinators \
  -H "Authorization: Bearer $TOKEN"

# Should show 5 coordinators by section
```

- [ ] 5 coordinators listed
- [ ] Designations like "Pre-Primary Coordinator", "Middle Coordinator"

---

## 🧪 **Test 6: Authentication & Role-Based Access**

### Test Admin Role
- [ ] Can access: `/api/leaves`, `/api/export`, `/api/notifications`
- [ ] Can approve/reject leaves
- [ ] Can export any PDF

### Test Teacher Role
- [ ] Can request leave
- [ ] Can view own notifications
- [ ] Can view own timetable
- [ ] Cannot approve other's leaves
- [ ] Cannot export admin reports

### Test Principal Role
- [ ] Can see dashboard
- [ ] Can view all leave requests
- [ ] Can see reports

### Test Different User Logins
```bash
# Try all test accounts
# 1. admin@school.edu / admin123
# 2. principal@school.edu / principal123
# 3. anjali@school.edu / coordinator123
# 4. priya.sharma@school.edu / teacher123

# Each should:
# - Login successfully (200 OK, token returned)
# - NOT see 401 errors
# - Access only their allowed features
```

- [ ] Admin: Full access
- [ ] Principal: Dashboard + approvals
- [ ] Coordinator: Section management
- [ ] Teacher: My classes + leave request
- [ ] All: No 401 errors after login

**✅ PASS**: Each role works correctly with proper permissions  
**❌ FAIL**: Roles can access what they shouldn't, or authentication fails

---

## 🧪 **Test 7: Performance**

### PDF Export Speed
```bash
# Time the PDF export
time curl http://localhost:5000/api/export/timetable/batch/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o /dev/null
```

- [ ] Should complete in < 5 seconds
- [ ] No timeouts

### Query Performance
```bash
# Time getting all teachers
time curl http://localhost:5000/api/teachers \
  -H "Authorization: Bearer $TOKEN" \
  -o /dev/null

# Should be < 100ms
```

- [ ] Queries respond quickly (< 100ms)
- [ ] No database locks or errors

### Concurrent Requests
```bash
# Export multiple PDFs simultaneously
for i in {1..3}; do
  curl http://localhost:5000/api/export/timetable/batch/$i \
    -H "Authorization: Bearer $TOKEN" \
    -o ~/Downloads/batch_$i.pdf &
done
wait

# All should succeed
ls -lh ~/Downloads/batch_*.pdf
```

- [ ] All complete without errors
- [ ] No "file already in use" errors

**✅ PASS**: All operations complete within acceptable time  
**❌ FAIL**: Slow (> 5 sec), timeouts, or errors

---

## ✅ **Final Validation**

After all tests pass, verify:

```bash
# 1. Database intact
sqlite3 timetable.db "SELECT COUNT(*) FROM students, teachers, coordinators, houses;"

# 2. Backend running
curl http://localhost:5000/api/teachers -H "Authorization: Bearer $TOKEN" | jq '.[:1]'

# 3. Frontend loads
curl http://localhost:3000 | grep -o "<title>.*</title>"

# 4. No errors in backend logs (check Flask terminal)
# 5. No errors in frontend console (check browser F12)
```

---

## 📊 Summary Check

| Feature | Status | Notes |
|---------|--------|-------|
| **Database** | ✅/❌ | 2,800 students loaded? |
| **PDF Export** | ✅/❌ | < 5 seconds, professional? |
| **Leave Request** | ✅/❌ | Teacher can request? |
| **Leave Approval** | ✅/❌ | Admin can approve with substitute? |
| **Timetable Update** | ✅/❌ | Updated after approval? |
| **Notifications** | ✅/❌ | Created and visible? |
| **Student Data** | ✅/❌ | 2,800 students retrievable? |
| **Teacher Data** | ✅/❌ | 75 teachers retrievable? |
| **Authentication** | ✅/❌ | All 4 roles work? |
| **Performance** | ✅/❌ | Queries fast (< 100ms)? |

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| "no such table: students" | Run `python backend/seed_realistic.py` |
| "401 Unauthorized" | Get fresh token from login endpoint |
| PDF export fails | Check admin role, valid batch ID |
| Leave approval error | Check teacher exists, substitute available |
| Database still empty (0 bytes) | Seed script didn't run or had error |
| Port 5000 in use | Use `flask run --port=5001` |

---

## ✨ Test Success Criteria

You've succeeded when:
- ✅ Database has 2,800 students + 75 teachers
- ✅ Can login without 401 errors
- ✅ Can export PDF timetables (< 5 seconds)
- ✅ Can request leave as teacher
- ✅ Can approve leave as admin (with substitute)
- ✅ Timetable updates automatically
- ✅ Notifications appear for all events
- ✅ All queries respond quickly
- ✅ All test accounts work with proper permissions

**🎉 If all above pass → System is READY for production!**
