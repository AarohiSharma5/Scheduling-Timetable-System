# Conflict Detection Quick Reference

## For the Impatient Developer 🚀

### What is This?
Your timetable validation engine that automatically detects scheduling conflicts and gaps after timetable generation.

### Where Is It?
- **Backend Engine**: `backend/conflict_detector.py` & `backend/conflict_validator.py`
- **Frontend Display**: `frontend/src/components/TimetableValidation.tsx`
- **Where It's Used**: `ReviewPage.tsx` (Conflict Validation tab)

### How It Works (30 Seconds)
1. User generates timetable
2. Frontend calls `GET /timetable/{id}/validate`
3. Backend detects conflicts (teacher overlaps, missing subjects, etc.)
4. Returns report with errors, warnings, gaps, and stats
5. Frontend displays report with collapsible sections and visual indicators
6. User can re-validate after making changes

### Key Features
✅ Detects teacher scheduling conflicts  
✅ Detects classroom double-bookings  
✅ Identifies missing subject periods (gaps)  
✅ Calculates slot usage statistics  
✅ Produces health score (valid/warning/error)  
✅ Expandable error details  
✅ Re-validation on demand  

### Quick Configuration
```python
# backend/config.py
SUBJECT_GAP_THRESHOLD = 0      # 0 = no gaps allowed
WORKLOAD_IMBALANCE = 20         # Max % difference in teacher load
MIN_SLOTS_PER_DAY = 4           # Minimum teaching slots/day
```

### Testing It
```bash
# Generate timetable with conflicts
curl -X POST http://localhost:5000/plans/{plan_id}/generate

# Validate (after generation)
curl http://localhost:5000/timetable/{timetable_id}/validate

# Frontend: Go to ReviewPage and click "Conflict Validation" tab
```

### Common Conflict Types
| Issue | Cause | Fix |
|-------|-------|-----|
| 🔴 TeacherConflict | Teacher assigned 2 classes same period | Move one class |
| 🔴 BatchConflict | Class assigned 2 subjects same period | Reschedule subject |
| 🟡 SubjectGap | Subject has <required periods | Add more periods |
| 🟡 Workload Imbalance | Teacher has too much/little load | Rebalance |

### API Quick Ref
```javascript
// Get full validation report
GET /timetable/{id}/validate

// Get just statistics
GET /timetable/{id}/conflicts/summary

// Get grouped by type
GET /timetable/{id}/conflicts/by-type

// Frontend usage
const report = await api.timetable.validate(timetableId);
```

### Response Structure
```json
{
  "is_valid": false,
  "errors": [{type, message, details}],
  "warnings": [{type, message, details}],
  "gaps": [{subject, batch_id, periods_missing}],
  "stats": {
    "total_slots": 480,
    "scheduled_slots": 450,
    "empty_slots": 30,
    "teachers_affected": 2,
    "batches_affected": 3
  },
  "summary": {
    "total_errors": 1,
    "total_warnings": 2,
    "total_gaps": 1,
    "conflict_free": false
  }
}
```

### Debugging
```bash
# Check backend logs
docker logs timetable-backend | grep -i conflict

# Check validation endpoint
curl -H "Authorization: Bearer {token}" \
  http://localhost:5000/timetable/1/validate | jq

# Frontend console
console.log('Validation report:', validationReport);
```

### Performance
- Validates 500-slot timetable in ~200ms
- Caches results for 5 minutes
- O(n²) algorithm (acceptable for typical schools)

### Customization
```tsx
// Use in your component
import TimetableValidation from '../components/TimetableValidation';

<TimetableValidation 
  timetableId={5}
  onValidationComplete={(report) => {
    console.log('Validated!', report);
  }}
/>
```

### Common Issues
| Problem | Cause | Solution |
|---------|-------|----------|
| Validation 404 | Timetable doesn't exist | Generate timetable first |
| Always shows errors | Gap threshold too strict | Check `SUBJECT_GAP_THRESHOLD` |
| Slow validation | Large timetable | Consider background jobs |
| No gaps detected | Gap detection disabled | Check backend logic |

### File Navigation
```
📁 Conflict Detection System
├── 🔧 BACKEND
│   ├── conflict_detector.py      ← Core logic
│   ├── conflict_validator.py     ← Validation runner
│   ├── models.py                 ← Data structures
│   └── timetable_routes.py       ← API endpoints
├── 🎨 FRONTEND
│   ├── TimetableValidation.tsx   ← Display component
│   ├── ReviewPage.tsx            ← Integration point
│   └── api.ts                    ← API client
└── 📚 DOCS
    ├── CONFLICT_VALIDATION_GUIDE.md    ← Deep dive
    ├── CONFLICT_DETECTION_STATUS.md    ← Implementation status
    └── CONFLICT_QUICK_REFERENCE.md     ← This file
```

### Links
- **Full Guide**: `CONFLICT_VALIDATION_GUIDE.md`
- **Status**: `CONFLICT_DETECTION_STATUS.md`
- **Backend Code**: `backend/conflict_detector.py`
- **Frontend Code**: `frontend/src/components/TimetableValidation.tsx`

---

**TL;DR**: Generates havesbacked timetables? Get validation report via API → display it in UI → user fixes conflicts → re-validate → publish ✅
