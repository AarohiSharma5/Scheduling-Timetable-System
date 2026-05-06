class PlannerService:
    WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    @staticmethod
    def build_timetable(school_profile, teachers, subjects):
        days_per_week = school_profile.get("days_per_week", 5)
        periods_per_day = school_profile.get("periods_per_day", 6)
        
        timetable = [[None for _ in range(periods_per_day)] for _ in range(days_per_week)]
        teacher_load = {t["id"]: 0 for t in teachers}
        teacher_max = {t["id"]: t.get("contact_hours", 24) for t in teachers}
        warnings = []
        
        core_subjects = [s for s in subjects if s.get("is_core", True)]
        active_electives = [s for s in subjects if not s.get("is_core", False)][:school_profile.get("elective_limit", 10)]
        all_subjects = sorted(core_subjects + active_electives, key=lambda x: x.get("periods_required", 1), reverse=True)
        
        for subject in all_subjects:
            teacher_id = subject.get("teacher_id")
            periods_needed = subject.get("periods_required", 1)
            
            if not teacher_id:
                warnings.append(f"Subject '{subject['name']}' has no teacher")
                continue
            
            for _ in range(periods_needed):
                day_loads = [(i, sum(1 for slot in timetable[i] if slot)) for i in range(days_per_week)]
                least_loaded = min(day_loads, key=lambda x: x[1])[0]
                
                for period in range(periods_per_day):
                    if timetable[least_loaded][period] is None:
                        teacher_name = next((t["name"] for t in teachers if t["id"] == teacher_id), "Unknown")
                        timetable[least_loaded][period] = {
                            "subject": subject["name"], "teacher": teacher_name,
                            "subject_id": subject["id"], "teacher_id": teacher_id,
                        }
                        teacher_load[teacher_id] += 1
                        break
            
            if teacher_load[teacher_id] > teacher_max[teacher_id]:
                warnings.append(f"Teacher load exceeded for {next((t['name'] for t in teachers if t['id'] == teacher_id), 'Unknown')}")
        
        return timetable, warnings

class FormParser:
    @staticmethod
    def html_escape(text):
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")) if text else text
    
    @staticmethod
    def url_decode(encoded):
        import urllib.parse
        return urllib.parse.unquote_plus(encoded)
    
    @staticmethod
    def parse_form_data(form_dict):
        return {k: FormParser.url_decode(v) if isinstance(v, str) else v for k, v in form_dict.items()}
