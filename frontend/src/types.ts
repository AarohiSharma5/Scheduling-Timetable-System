export interface SchoolProfile {
  institution_name: string;
  days_per_week: number;
  periods_per_day: number;
  student_count: number;
  core_subjects_target: number;
  elective_limit: number;
}

export interface Teacher {
  id: number;
  name: string;
  contact_hours: number;
  expertise: string[];
}

export interface Subject {
  id: number;
  name: string;
  teacher_id: number;
  is_core: boolean;
  periods_required: number;
}

export interface TimetableSlot {
  subject: string;
  teacher: string;
  subject_id: number;
  teacher_id: number;
}

export interface Plan {
  id: number;
  user_id: number;
  title: string;
  description: string;
  school_profile: SchoolProfile;
  teachers: Teacher[];
  subjects: Subject[];
  timetable?: (TimetableSlot | null)[][];
  warnings?: string[];
  status: "draft" | "completed";
  created_at: string;
  updated_at: string;
}

// Teacher Dashboard Interfaces
export interface ScheduleClass {
  periodIndex: number;
  subjectName: string;
  subjectId: number;
  batchName: string;
  batchId: number;
  isCore: boolean;
  day: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday";
  dayIndex: number;
  time?: string;
}

export interface TeacherSchedule {
  teacherId: number;
  teacherName: string;
  dailyClasses: {
    [key: string]: (ScheduleClass | null)[];
  };
  todaysClasses: ScheduleClass[];
  totalPeriodsThisWeek: number;
  freePeriodsToday: number[];
}

export interface PeriodInfo {
  index: number;
  time?: string;
}

export interface DaySchedule {
  dayName: string;
  dayIndex: number;
  periods: (ScheduleClass | null)[];
}

// Student Dashboard Interfaces
export interface StudentClass {
  periodIndex: number;
  subjectName: string;
  subjectId: number;
  teacherName: string;
  teacherId: number;
  isCore: boolean;
  duration: string;
  room?: string;
  day: string;
  dayIndex: number;
}

export interface StudentSchedule {
  studentId: number;
  studentName: string;
  batchName: string;
  batchId: number;
  dailyClasses: {
    [key: string]: (StudentClass | null)[];
  };
  todaysClasses: StudentClass[];
  totalPeriodsThisWeek: number;
  freePeriodsToday: number[];
  lunchtimeSlot: number;
}

export interface StudentTimetableDay {
  dayName: string;
  dayIndex: number;
  periods: (StudentClass | null)[];
  freePeriodsCount: number;
}

// Principal Dashboard Analytics Interfaces
export interface TeacherAnalytics {
  teacherId: number;
  teacherName: string;
  subjectName: string;
  totalPeriodsAssigned: number;
  maxPeriodsCapacity: number;
  workloadPercentage: number;
  assignedBatches: number;
  hasSpecialDuties: boolean;
  daysLate?: string[];
}

export interface BatchCompletion {
  batchId: number;
  batchName: string;
  studentCount: number;
  totalSlotsAvailable: number;
  slotsFilled: number;
  completionPercentage: number;
  missingSubjects: string[];
}

export interface SubjectAssignment {
  subjectId: number;
  subjectName: string;
  periodsRequired: number;
  periodsAssigned: number;
  assignedTeachers: number;
  isFullyAssigned: boolean;
  batchesNeedingIt: string[];
}

export interface TimetableAnalytics {
  totalTeachers: number;
  totalBatches: number;
  totalSubjects: number;
  totalPeriodsAvailable: number;
  totalPeriodsAssigned: number;
  occupancyPercentage: number;
  averageTeacherWorkload: number;
  averageBatchCompletion: number;
  teacherAnalytics: TeacherAnalytics[];
  batchCompletion: BatchCompletion[];
  subjectAssignments: SubjectAssignment[];
  freeSlots: number;
  conflictCount: number;
  warnings: string[];
}

export interface AnalyticsCard {
  title: string;
  value: string | number;
  unit: string;
  icon: string;
  color: "blue" | "green" | "yellow" | "red" | "purple" | "indigo";
  trend?: "up" | "down" | "stable";
  trendValue?: string;
}
