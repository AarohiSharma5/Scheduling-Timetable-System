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
  day: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday";
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
