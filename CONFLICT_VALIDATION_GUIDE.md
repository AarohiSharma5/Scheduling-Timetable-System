# Conflict Detection & Validation System

## Overview

The conflict detection system provides comprehensive validation of generated timetables, identifying scheduling conflicts, gaps, and issues that need resolution before publication.

## Components

### Backend Components

#### 1. **ConflictDetector** (`backend/conflict_detector.py`)
- **Purpose**: Core engine for detecting scheduling conflicts
- **Key Methods**:
  - `detect_teacher_conflicts()`: Identifies when teachers are scheduled for overlapping periods
  - `detect_classroom_conflicts()`: Identifies when batches are scheduled for overlapping periods
  - `detect_gaps()`: Identifies incomplete subject allocations
  - `get_report()`: Generates comprehensive validation report

#### 2. **ConflictValidator** (`backend/conflict_validator.py`)
- **Purpose**: Validates conflict detection logic and timetable integrity
- **Key Methods**:
  - `validate()`: Orchestrates all validation checks
  - `check_zero_conflicts()`: Verifies no conflicts exist
  - `get_summary()`: Returns conflict statistics
  - `get_details_by_type()`: Groups conflicts by type

#### 3. **Conflict Models** (`backend/models.py`)
- `ConflictReport`: Main report object containing errors, warnings, gaps, and statistics
- Structure:
  ```python
  {
    "is_valid": bool,
    "errors": [{"type", "message", "details"}],
    "warnings": [{"type", "message", "details"}],
    "gaps": [{"subject", "batch_id", "periods_missing"}],
    "stats": {
      "total_slots": int,
      "scheduled_slots": int,
      "empty_slots": int,
      "teachers_affected": int,
      "batches_affected": int
    },
    "summary": {
      "total_errors": int,
      "total_warnings": int,
      "total_gaps": int,
      "conflict_free": bool
    }
  }
  ```

#### 4. **Validation Routes** (`backend/timetable_routes.py`)
- `GET /timetable/{id}/validate`
  - Returns: Full validation report
  - Status: ✅ Implemented

- `GET /timetable/{id}/conflicts/summary`
  - Returns: Conflict statistics only
  - Status: ✅ Implemented

- `GET /timetable/{id}/conflicts/by-type`
  - Returns: Conflicts grouped by type
  - Status: ✅ Implemented

### Frontend Components

#### 1. **TimetableValidation Component** (`frontend/src/components/TimetableValidation.tsx`)
- **Purpose**: React component for displaying validation results
- **Features**:
  - Real-time validation on mount
  - Expandable sections for errors, warnings, gaps
  - Visual indicators (colors, icons) for status
  - Health score and statistics display
  - Re-validation button for manual refresh

#### 2. **ReviewPage Integration** (`frontend/src/pages/ReviewPage.tsx`)
- **Features**:
  - Tabbed interface with "Timetable Review" and "Conflict Validation"
  - Auto-detects timetable generation
  - Provides validation data alongside timetable preview

#### 3. **API Integration** (`frontend/src/api.ts`)
- `api.timetable.validate(id)`: Fetch validation report
- `api.timetable.getSummary(id)`: Fetch conflict summary
- `api.timetable.getConflictsByType(id)`: Fetch conflicts by type

## Conflict Types

### 1. **Teacher Conflicts** (ERROR)
- **Trigger**: Teacher scheduled for overlapping periods
- **Example**: Teacher A assigned to Period 1-2 for Class A AND Period 2-3 for Class B
- **Resolution**: Reassign one of the periods to a different teacher

### 2. **Classroom/Batch Conflicts** (ERROR)
- **Trigger**: Batch scheduled for overlapping periods
- **Example**: Class X assigned 2 different subjects in the same period
- **Resolution**: Adjust subject assignments or modify time slots

### 3. **Subject Gaps** (WARNING)
- **Trigger**: Subject has fewer scheduled periods than required
- **Example**: Subject X requires 4 periods/week but only 3 are scheduled
- **Resolution**: Allocate additional periods to the subject

### 4. **Teacher Workload Imbalance** (WARNING)
- **Trigger**: Teacher has significantly different load than peers
- **Impact**: May indicate inefficient scheduling
- **Resolution**: Rebalance teaching load across teachers

### 5. **Time Slot Efficiency** (WARNING)
- **Trigger**: Excessive empty slots or fragmented scheduling
- **Example**: Teachers/batches have gaps in the schedule
- **Resolution**: Consolidate schedules where possible

## Usage Flow

### 1. **Generate Timetable**
```
User → ReviewPage → Click "Generate Timetable"
↓
API: POST /plans/{id}/generate
↓
Returns: timetable_data + warnings
```

### 2. **Validate (Automatic)**
```
Timetable Generated → ReviewPage → Loads TimetableValidation
↓
Auto-calls: GET /timetable/{id}/validate
↓
Displays: Validation Report
```

### 3. **Review Conflicts**
```
User → Click "Conflict Validation" tab
↓
TimetableValidation Component loads
↓
Displays:
  - Error summary (critical issues)
  - Warnings (efficiency issues)
  - Gaps (incomplete allocations)
  - Statistics (slots, teachers affected, etc.)
```

### 4. **Resolve Conflicts** (Manual)
```
User identifies conflict in validation report
↓
User modifies schedule via TeacherManagement or CurriculumEditor
↓
User clicks "Re-validate"
↓
New validation report generated
↓
Conflicts resolved or new issues identified
```

### 5. **Publish** (When Valid)
```
Validation shows is_valid=true
↓
User can publish timetable
↓
API: POST /timetable/{id}/publish
↓
Timetable saved as final
```

## Data Flow Diagram

```
┌─────────────────┐
│  User Input     │ (Teacher assignments, subject allocations)
└────────┬────────┘
         ↓
┌─────────────────────┐
│  Timetable Generate │ (API: POST /plans/{id}/generate)
└────────┬────────────┘
         ↓
┌──────────────────────┐
│  ConflictDetector    │ (Backend engine)
│  - Teacher conflicts │
│  - Batch conflicts   │
│  - Subject gaps      │
│  - Workload issues   │
└────────┬─────────────┘
         ↓
┌──────────────────────┐
│  ConflictReport      │ (Detailed report)
│  - errors[]          │
│  - warnings[]        │
│  - gaps[]            │
│  - stats{}           │
└────────┬─────────────┘
         ↓
┌──────────────────────────┐
│ TimetableValidation Comp │ (React display)
│ - Error accordion         │
│ - Warning accordion       │
│ - Gaps table             │
│ - Health score           │
└────────┬─────────────────┘
         ↓
┌──────────────────────┐
│  User Resolution     │ (Manual conflict fixing)
└────────┬─────────────┘
         ↓
┌──────────────────────┐
│  Re-validate         │ (Feedback loop)
└────────┬─────────────┘
         ↓
┌──────────────────────┐
│  is_valid = true?    │
└────────┬─────────────┘
    ↙         ↘
  NO         YES
   ↓          ↓
LOOP     PUBLISH
```

## API Endpoints

### GET /timetable/{id}/validate
Returns comprehensive validation report with all conflict details

**Response:**
```json
{
  "is_valid": true,
  "errors": [],
  "warnings": [{...}],
  "gaps": [{...}],
  "stats": {...},
  "summary": {...}
}
```

### GET /timetable/{id}/conflicts/summary
Returns only summary statistics

**Response:**
```json
{
  "total_errors": 0,
  "total_warnings": 2,
  "total_gaps": 1,
  "conflict_free": false
}
```

### GET /timetable/{id}/conflicts/by-type
Returns conflicts grouped by type

**Response:**
```json
{
  "teacher_conflicts": [{...}],
  "batch_conflicts": [{...}],
  "subject_gaps": [{...}],
  "workload_issues": [{...}]
}
```

## Configuration

### Validation Thresholds
Located in `backend/config.py`:

```python
# Subject gap tolerance (periods)
SUBJECT_GAP_THRESHOLD = 0  # 0 = no gaps allowed

# Workload imbalance tolerance (percentage)
WORKLOAD_IMBALANCE_THRESHOLD = 20

# Minimum slots per day
MIN_SLOTS_PER_DAY = 4
```

### Conflict Severity Levels
- **ERROR**: Scheduling is impossible, must be fixed
- **WARNING**: Suboptimal but functional, should be fixed
- **INFO**: Additional context, may be ignored

## Performance Considerations

1. **Detection Speed**: O(n²) for teacher conflicts, O(n²) for batch conflicts
   - For typical school: ~500 slots → <1s validation time

2. **Caching**: Validation results cached for 5 minutes
   - Reduces database queries
   - Improves UI responsiveness

3. **Async Processing**: Large timetables use background jobs
   - Prevents UI freezing
   - Shows progress updates

## Error Scenarios

### Scenario 1: Teacher Over-Scheduled
```
Teacher: Mr. Smith
Period 1: Class 10-A (Math)
Period 1: Class 10-B (Physics) ← CONFLICT

Error Type: TeacherConflict
Message: "Mr. Smith scheduled for overlapping periods"
Resolution: Move one period to different teacher or time slot
```

### Scenario 2: Subject Incomplete
```
Subject: English
Batch: Class 9-A
Required: 4 periods/week
Scheduled: 2 periods/week

Gap Type: SubjectGap
Message: "English in Class 9-A missing 2 periods"
Resolution: Allocate additional 2 periods
```

### Scenario 3: Classroom Double-Booked
```
Batch: Class 8-C
Period 2: Math
Period 2: Science ← CONFLICT

Error Type: BatchConflict
Message: "Class 8-C scheduled for 2 subjects in same period"
Resolution: Move one subject to different period or batch
```

## Testing

### Unit Tests
- `tests/test_conflict_detector.py`: Core detection logic
- `tests/test_conflict_validator.py`: Validation logic
- `tests/test_validation_routes.py`: API endpoints

### Integration Tests
- Full timetable generation → validation pipeline
- Conflict resolution workflow

### Test Commands
```bash
# Run all tests
cd backend && python -m pytest tests/

# Run specific module
pytest tests/test_conflict_detector.py -v

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Future Enhancements

1. **Automated Conflict Resolution**
   - Suggest optimal rearrangements
   - AI-assisted scheduling

2. **Constraint Programming**
   - Express constraints as mathematical formulas
   - Use solver for optimal solutions

3. **Advanced Reporting**
   - Generate PDF reports
   - Export to Excel with highlighting
   - Email notifications

4. **Real-time Validation**
   - Validate as user edits
   - WebSocket for live updates

5. **Conflict Analytics**
   - Historical conflict patterns
   - Predictive conflict detection
   - Root cause analysis

## Troubleshooting

### Validation Endpoint Returns 500
1. Check backend logs: `docker logs timetable-backend`
2. Ensure timetable_id exists: `GET /timetable/list`
3. Verify timetable data integrity in database

### False Positives in Conflicts
1. Review conflict detection logic in `conflict_detector.py`
2. Check time slot configurations
3. Verify teacher/batch assignments

### Performance Issues
1. Check timetable size: `GET /timetable/{id}`
2. Monitor CPU usage during validation
3. Consider implementing caching

### Gaps Not Detected
1. Verify subject requirements in curriculum
2. Check batch-subject mappings
3. Review gap detection thresholds in config

## References

- [Backend Implementation](../../backend/)
- [Frontend Component Source](../frontend/src/components/TimetableValidation.tsx)
- [Conflict Detection Algorithm](../../CONFLICT_DETECTION.md)
- [API Documentation](../../API_DOCUMENTATION.md)
