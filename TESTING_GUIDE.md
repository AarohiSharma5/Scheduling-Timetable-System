# 🎓 Teacher Dashboard - Complete Testing Guide

## 📋 Overview

Your School Timetable system is now populated with **sample data** and ready for testing. This guide provides all the credentials and instructions to test the **Teacher Dashboard** and all its features.

---

## 🚀 Quick Start

### 1. Start the Application

```bash
cd /Users/aarohi_sharma/cpp\ project
docker-compose up -d
```

Wait 30-60 seconds for services to start, then access:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:3000/api
- **Health Check**: http://localhost:3000/api/health

### 2. Login and Test

Go to http://localhost:3000 and use any of the credentials below.

---

## 👥 Test Accounts

### **TEACHERS** (Best for testing Teacher Dashboard)

| Name | Email | Password | Subjects | Classes |
|------|-------|----------|----------|---------|
| **Priya Verma** | priya.verma@school.edu | teacher123 | English | Grade 9-A, Grade 10-A |
| **Rajesh Kumar** | rajesh.kumar@school.edu | teacher123 | Mathematics | Grade 9-A, Grade 9-B, Grade 10-A |
| **Anjali Singh** | anjali.singh@school.edu | teacher123 | Physics, Chemistry | Grade 10-A, Grade 10-B |
| **Vikram Patel** | vikram.patel@school.edu | teacher123 | Biology | Grade 10-A, Grade 10-B |
| **Meera Desai** | meera.desai@school.edu | teacher123 | History, Geography | Grade 9-A, Grade 9-B |
| **Arjun Nair** | arjun.nair@school.edu | teacher123 | Physical Education | Multi-grade |
| **Pooja Gupta** | pooja.gupta@school.edu | teacher123 | Computer Science | Grade 10-A, Grade 10-B |
| **Sanjay Rao** | sanjay.rao@school.edu | teacher123 | Civics | Grade 9-A, Grade 9-B, Grade 10-A |

### **STUDENTS** (To view student perspective)

| Email | Password | Class |
|-------|----------|-------|
| student9A1@school.edu | student123 | Grade 9-A |
| student9A2@school.edu | student123 | Grade 9-A |
| student9A3@school.edu | student123 | Grade 9-A |
| student9B1@school.edu | student123 | Grade 9-B |
| student10A1@school.edu | student123 | Grade 10-A |
| student10B1@school.edu | student123 | Grade 10-B |
| *(+12 more)* | student123 | *(Various grades)* |

### **ADMIN / PRINCIPAL**

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@school.edu | admin123 |
| Principal | principal@school.edu | principal123 |

---

## ✅ Features to Test - Teacher Dashboard

### **1. Weekly Timetable Grid** ✅
- **What to see**: A 5-day × 6-period table showing the entire weekly schedule
- **Login as**: priya.verma@school.edu
- **Expected**: 
  - Monday through Friday columns
  - 6 periods per day
  - Classes assigned to Priya for Grade 9-A and 10-A

### **2. Subjects Per Period** ✅
- **What to see**: Subject names clearly displayed in each time slot
- **Login as**: Any teacher account
- **Expected**: 
  - Period 1 (Mon): English
  - Period 2 (Tue): Mathematics
  - Period 3 (Wed): Physics, etc.

### **3. Batch/Class Information** ✅
- **What to see**: Class/Grade information (e.g., "Grade 9 - Section A")
- **Login as**: rajesh.kumar@school.edu
- **Expected**:
  - Batch label shown in each slot
  - Example: "Grade 9-A", "Grade 10-B"
  - Shows which classes each teacher teaches

### **4. Free Periods Highlighted** ✅
- **What to see**: Free/unassigned periods in yellow background
- **Login as**: arjun.nair@school.edu (has PE duties, so fewer periods)
- **Expected**:
  - Yellow background for free periods
  - Warning icon (⚠️) indicating available time
  - Easy to spot at a glance

### **5. Today's Classes Summary** ✅
- **What to see**: Quick summary card at the top showing today's schedule
- **Login as**: Any teacher
- **Expected**:
  - Shows count: "You have X classes today"
  - Lists all classes for current day
  - Shows time and subject for each class

### **6. Daily Navigation** ✅
- **What to see**: Day selector buttons to switch between days
- **Login as**: Any teacher
- **Expected**:
  - Click different day buttons
  - View changes to show that day's detail
  - Today's day is highlighted

### **7. Responsive Design** ✅
- **What to see**: Works on mobile, tablet, and desktop
- **Login as**: Any teacher
- **Test on**:
  - Desktop: Full width table with all details
  - Tablet (iPad): Adjusted layout
  - Mobile (iPhone): Scrollable, optimized view

### **8. Analytics Section** ✅
- **What to see**: Statistics and breakdown of teaching load
- **Login as**: Any teacher
- **Expected**:
  - Total periods this week
  - Breakdown by day
  - Subject distribution
  - Free periods count

---

## 📊 Sample Timetable Data

### **Classes in System** (6 Batches)
- Grade 9 - Section A (45 students)
- Grade 9 - Section B (42 students)
- Grade 10 - Section A (48 students)
- Grade 10 - Section B (46 students)
- Grade 11 - Section A (40 students)
- Grade 12 - Section A (38 students)

### **Subjects Available** (10 Total)
1. English (4 periods/week)
2. Mathematics (4 periods/week)
3. Physics (3 periods/week)
4. Chemistry (3 periods/week)
5. Biology (2 periods/week)
6. History (3 periods/week)
7. Geography (2 periods/week)
8. Civics (2 periods/week)
9. Physical Education (2 periods/week)
10. Computer Science (2 periods/week)

### **Complete Weekly Schedule**

| Day | Period 1 | Period 2 | Period 3 | Period 4 | Period 5 | Period 6 |
|-----|----------|----------|----------|----------|----------|----------|
| **Mon** | English (9A) | Math (9A) | Physics (10A) | 🍽️ Lunch | History (9A) | P.E. (9A) |
| **Tue** | Math (9A) | Chemistry (10A) | CS (10A) | 🍽️ Lunch | English (9A) | Civics (9A) |
| **Wed** | Physics (10A) | Biology (10A) | English (9A) | 🍽️ Lunch | Math (9A) | P.E. (9A) |
| **Thu** | History (9A) | CS (10A) | Math (9A) | 🍽️ Lunch | Chemistry (10A) | Civics (9A) |
| **Fri** | English (9A) | Biology (10A) | Geography (9A) | 🍽️ Lunch | CS (10A) | P.E. (9A) |

---

## 🎯 Testing Checklist

Use this checklist to verify all features work:

### Priya Verma Test (priya.verma@school.edu / teacher123)
- [ ] Login successful
- [ ] Dashboard loads without errors
- [ ] Weekly grid shows 5 days
- [ ] Weekly grid shows 6 periods per day
- [ ] Monday Period 1: English shown
- [ ] Batch "Grade 9-A" visible
- [ ] Free periods highlighted in yellow
- [ ] Today's summary shows classes for today
- [ ] Can click day buttons and see changes
- [ ] Mobile view is responsive
- [ ] Analytics show correct totals

### Rajesh Kumar Test (rajesh.kumar@school.edu / teacher123)
- [ ] Login successful
- [ ] Shows Math (4 periods/week)
- [ ] Teaches Grade 9-A, 9-B, and 10-A
- [ ] Tuesday Period 2: Chemistry (not his class, should be free)
- [ ] Validate all 3 batches appear in schedule

### Teacher with Duties Test (arjun.nair@school.edu / teacher123)
- [ ] Login successful
- [ ] Shows Physical Education
- [ ] Has free periods throughout week (yellow highlighting)
- [ ] Max capacity is 60% (14 periods) due to PE duties

### General Tests
- [ ] All 8 teachers can login
- [ ] All students can login  
- [ ] Students see their batch's timetable
- [ ] Admin can access admin panel
- [ ] Principal can see stats dashboard
- [ ] No console errors in browser DevTools
- [ ] API responds quickly (< 500ms)

---

## 🔍 Troubleshooting

### Issue: "Can't connect to API"
**Solution**: Make sure backend is running
```bash
docker-compose ps
# Should show: postgres and backend as "Up"
```

### Issue: "Invalid credentials"
**Solution**: Check spelling - passwords are case-sensitive:
- Teachers: `teacher123` (lowercase)
- Students: `student123` (lowercase)
- Admin: `admin123` (lowercase)

### Issue: "No timetable data showing"
**Solution**: The timetable has been generated and published. If not showing:
1. Check if user is teacher: `http://localhost:3000/api/plans`
2. Should return an array with plan object

### Issue: "Yellow highlighting not showing"
**Solution**: Free periods should show yellow background. If not:
1. Check browser DevTools (F12) for CSS errors
2. Verify Tailwind CSS is loaded
3. Try Ctrl+Shift+R (hard refresh)

### Issue: "Classes don't match my teacher"
**Solution**: 
- Priya: Grade 9-A, 10-A (English)
- Rajesh: Grade 9-A, 9-B, 10-A (Math)
- Other teachers have different assignments
- Check the assignment in the table above

---

## 📈 What's Working

✅ Database with 28 users (8 teachers, 18 students, admin, principal)
✅ Complete 5-day × 6-period timetable with 30 slots
✅ Teacher assignments for each class
✅ Subject mapping to periods
✅ Batch/class information
✅ Free period detection
✅ Responsive design (mobile, tablet, desktop)
✅ TeacherDashboard component with all 5 features
✅ Weekly grid display
✅ Today's schedule summary
✅ Analytics and statistics
✅ Proper authentication with JWT tokens

---

## 📱 Browser Testing

### Recommended Browsers
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### Mobile Testing
- Use Chrome DevTools responsive design mode
- Test phone sizes: 320px, 375px, 768px widths
- Check that table scrolls horizontally on tiny screens
- Verify all buttons are clickable on touch devices

---

## 🛠️ Advanced Testing

### View Raw Timetable Data
```bash
curl -X GET http://localhost:3000/api/plans
```

### Health Check
```bash
curl -X GET http://localhost:3000/api/health
```

### Check Database
```bash
docker exec -it $(docker ps -qf "name=postgres") psql -U postgres -d timetable_db
```

Inside psql:
```sql
SELECT COUNT(*) FROM timetable_slots;  -- Should show 30
SELECT COUNT(*) FROM users;             -- Should show 28
SELECT COUNT(*) FROM teachers;          -- Should show 8
```

---

## 📞 Support

If you encounter any issues:

1. **Check backend logs**:
   ```bash
   docker logs $(docker ps -qf "name=backend")
   ```

2. **Check frontend logs**: Open browser DevTools (F12) → Console

3. **Restart services**:
   ```bash
   docker-compose restart
   docker-compose logs -f
   ```

4. **Full reset** (if needed):
   ```bash
   docker-compose down
   docker-compose up -d
   python3 backend/seed.py  # Reseed database
   ```

---

## ✨ Next Steps

After testing is complete, you can:

1. **Deploy**: Push to production environment
2. **Customize**: Modify colors, add school branding, customize subjects
3. **Enhance**: Add room assignments, time slots, more analytics
4. **Integrate**: Connect with school management system, SIS, etc.
5. **Monitor**: Set up logging, error tracking, performance monitoring

---

## 📝 Feature Summary

| Feature | Status | Test Login | Expected Result |
|---------|--------|-----------|-----------------|
| **Weekly Grid** | ✅ Complete | priya.verma@school.edu | 5×6 table shows |
| **Subjects** | ✅ Complete | Any teacher | Subject names visible |
| **Batch Info** | ✅ Complete | rajesh.kumar@school.edu | Grade/Section shown |
| **Free Periods** | ✅ Complete | arjun.nair@school.edu | Yellow highlighting |
| **Today Summary** | ✅ Complete | Any teacher | Quick stats card |
| **Day Navigation** | ✅ Complete | Any teacher | Switchable days |
| **Responsive** | ✅ Complete | Mobile view | Adaptive layout |
| **Analytics** | ✅ Complete | Any teacher | Stats section |

---

**🎉 Enjoy! Your Teacher Dashboard is ready to use!**

Questions? Check the [Teacher Dashboard Guide](./TEACHER_DASHBOARD_GUIDE.md) for more details.
