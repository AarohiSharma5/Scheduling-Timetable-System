# 🔐 Quick Credentials & Testing Reference

## 🚀 Start the System

```bash
cd /Users/aarohi_sharma/cpp\ project
docker-compose up -d
# Wait 30-60 seconds
# Open: http://localhost:3000
```

---

## 👨‍🏫 TEACHERS (Best for Testing Teacher Dashboard)

### **Recommended to Test**

```
Email: priya.verma@school.edu
Password: teacher123
Subject: English | Classes: Grade 9-A, Grade 10-A
```

```
Email: rajesh.kumar@school.edu
Password: teacher123
Subject: Mathematics | Classes: Grade 9-A, Grade 9-B, Grade 10-A
```

```
Email: arjun.nair@school.edu
Password: teacher123
Subject: PE | Classes: Multi-grade (has duties - note fewer free periods possible)
```

### **All 8 Teachers Available**
- priya.verma@school.edu (English)
- rajesh.kumar@school.edu (Math)
- anjali.singh@school.edu (Physics, Chemistry)
- vikram.patel@school.edu (Biology)
- meera.desai@school.edu (History, Geography)
- arjun.nair@school.edu (PE)
- pooja.gupta@school.edu (Computer Science)
- sanjay.rao@school.edu (Civics)

**All use password**: `teacher123`

---

## 👨‍🎓 STUDENTS

```
Email: student9A1@school.edu
Password: student123
```

Available: student9A1-3, student9B1-3, student10A1-3, student10B1-3, student11A1-3, student12A1-3

---

## 🏫 ADMIN / PRINCIPAL

```
Admin
Email: admin@school.edu
Password: admin123

Principal
Email: principal@school.edu
Password: principal123
```

---

## ✅ Teacher Dashboard - Features Checklist

Login as **priya.verma@school.edu** / **teacher123**

- [ ] **Weekly Grid**: Shows Monday-Friday, 6 periods each
- [ ] **Subjects Per Period**: "English", "Math", etc. visible
- [ ] **Batch Info**: Shows "Grade 9-A", "Grade 10-B" style labels
- [ ] **Free Periods**: Highlighted in yellow with warning icon
- [ ] **Today's Summary**: Top card showing today's classes
- [ ] **Responsive**: Works on mobile, tablet, desktop
- [ ] **Analytics**: Shows class breakdown and stats

---

## 📊 Data Generated

- **6 Batches**: Grades 9, 10, 11, 12 (A & B sections)
- **10 Subjects**: English, Math, Physics, Chemistry, Biology, History, Geography, Civics, PE, CS
- **8 Teachers**: Each with specific subjects and class assignments
- **18 Students**: 3 per batch
- **30 Time Slots**: Complete week Mon-Fri, 6 periods/day plus lunch

---

## 🧪 Quick Tests

### Test 1: See Weekly Timetable
1. Login: priya.verma@school.edu / teacher123
2. See: 5×6 grid with classes
3. Expected: Monday English (Period 1), Math (Period 2), etc.

### Test 2: Check Free Periods
1. Login: arjun.nair@school.edu / teacher123
2. Look for: Yellow highlighted cells
3. Expected: Notice free time slots (has PE duties)

### Test 3: Mobile Responsive
1. Login with any teacher account
2. Open DevTools (F12) → Device toggle
3. Change to mobile size (320px width)
4. Expected: Table responsive, content readable

### Test 4: Different Teachers
1. Login: rajesh.kumar@school.edu / teacher123
2. vs.
3. Login: pooja.gupta@school.edu / teacher123
4. Compare: Different schedules, different classes

---

## 🔗 API Endpoints

```
GET /api/plans
GET /api/plans/{id}
GET /api/health
POST /api/auth/login
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't login | Check password is exactly: `teacher123` (lowercase) |
| No classes shown | Teacher might have no classes - try priya.verma@school.edu |
| Can't connect | Make sure: `docker-compose up -d` is running |
| Yellow highlighting missing | Refresh page with Ctrl+Shift+R |

---

## 📱 Today's Test Schedule

When you login, the dashboard shows "today's" schedule. Since this is sample data:
- **All 5 days** (Mon-Fri) have complete schedules
- **Today** is highlighted based on current day of week
- **Lunch** is Period 4 (12:00-12:45) for all classes

---

## 🎯 What to Show Others

1. **Weekly Grid**: Impressive 5×6 formatted timetable ✨
2. **Free Periods**: Yellow highlighting shows available time ⚠️
3. **Batch Info**: Clear labeling of which class has what ✅
4. **Responsive**: Shrink window → still works perfectly 📱
5. **Summary**: Today's stats at a glance 📊

---

**Ready to go! Start with priya.verma@school.edu 🎓**
