import React, { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { Teacher, Subject } from "../types";

export const CurriculumEditorComponent: React.FC<{
  teachers: Teacher[];
  subjects: Subject[];
  onTeachersChange: (teachers: Teacher[]) => void;
  onSubjectsChange: (subjects: Subject[]) => void;
}> = ({ teachers, subjects, onTeachersChange, onSubjectsChange }) => {
  const [newTeacher, setNewTeacher] = useState({ name: "", contact_hours: 24 });
  const [newSubject, setNewSubject] = useState({
    name: "",
    teacher_id: 0,
    is_core: true,
    periods_required: 1,
  });

  const addTeacher = () => {
    if (newTeacher.name.trim()) {
      const teacher: Teacher = {
        id: Date.now(),
        ...newTeacher,
        expertise: [],
      };
      onTeachersChange([...teachers, teacher]);
      setNewTeacher({ name: "", contact_hours: 24 });
    }
  };

  const removeTeacher = (id: number) => {
    onTeachersChange(teachers.filter((t) => t.id !== id));
  };

  const addSubject = () => {
    if (!newSubject.name.trim()) {
      return;
    }
    if (!newSubject.teacher_id) {
      alert("Please select a teacher for this subject");
      return;
    }
    const subject: Subject = {
      id: Date.now(),
      ...newSubject,
    };
    onSubjectsChange([...subjects, subject]);
    setNewSubject({
      name: "",
      teacher_id: 0,
      is_core: true,
      periods_required: 1,
    });
  };

  const removeSubject = (id: number) => {
    onSubjectsChange(subjects.filter((s) => s.id !== id));
  };

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold">Teachers</h3>
        <div className="mb-4 space-y-2">
          {teachers.map((teacher) => (
            <div key={teacher.id} className="flex items-center justify-between rounded bg-gray-100 p-2">
              <div>
                <p>{teacher.name}</p>
                <p className="text-sm text-gray-600">{teacher.contact_hours} hours/week</p>
              </div>
              <button
                onClick={() => removeTeacher(teacher.id)}
                className="bg-red-600 hover:bg-red-700"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <input
            type="text"
            placeholder="Teacher name"
            value={newTeacher.name}
            onChange={(e) => setNewTeacher({ ...newTeacher, name: e.target.value })}
          />
          <input
            type="number"
            placeholder="Contact hours/week"
            value={newTeacher.contact_hours}
            onChange={(e) =>
              setNewTeacher({ ...newTeacher, contact_hours: +e.target.value })
            }
            min="1"
            max="40"
          />
          <button onClick={addTeacher} className="w-full">
            <Plus size={16} className="mr-2 inline" /> Add Teacher
          </button>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold">Subjects</h3>
        <div className="mb-4 space-y-2">
          {subjects.map((subject) => (
            <div key={subject.id} className="flex items-center justify-between rounded bg-gray-100 p-2">
              <div>
                <p>{subject.name}</p>
                <p className="text-sm text-gray-600">
                  {subject.is_core ? "Core" : "Elective"} - {subject.periods_required}
                  periods
                </p>
              </div>
              <button
                onClick={() => removeSubject(subject.id)}
                className="bg-red-600 hover:bg-red-700"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <input
            type="text"
            placeholder="Subject name"
            value={newSubject.name}
            onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })}
          />
          <select
            value={newSubject.teacher_id || ""}
            onChange={(e) => setNewSubject({ ...newSubject, teacher_id: +e.target.value })}
          >
            <option value="">-- Select Teacher --</option>
            {teachers.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={newSubject.is_core}
              onChange={(e) => setNewSubject({ ...newSubject, is_core: e.target.checked })}
              className="mr-2"
            />
            Core Subject
          </label>
          <input
            type="number"
            placeholder="Periods per week"
            value={newSubject.periods_required}
            onChange={(e) => setNewSubject({ ...newSubject, periods_required: +e.target.value })}
            min="1"
            max="10"
          />
          <button onClick={addSubject} className="w-full">
            <Plus size={16} className="mr-2 inline" /> Add Subject
          </button>
        </div>
      </div>
    </div>
  );
};
