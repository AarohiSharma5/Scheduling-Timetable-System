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
