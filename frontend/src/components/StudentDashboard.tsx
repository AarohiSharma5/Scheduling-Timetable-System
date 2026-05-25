import React, { useState, useMemo } from "react";
import {
  Calendar,
  Clock,
  BookOpen,
  Users,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import type { Plan, StudentSchedule, StudentClass } from "../types";

interface StudentDashboardProps {
  plan: Plan;
  studentId: number;
  studentName: string;
  batchName: string;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri"];

export default function StudentDashboard({
  plan,
  studentId,
  studentName,
  batchName,
}: StudentDashboardProps) {
  const [selectedDay, setSelectedDay] = useState<number>(
    Math.max(0, Math.min(4, new Date().getDay() - 1))
  );

  // Parse timetable data for this batch/student
  const studentSchedule = useMemo(() => {
    const schedule: StudentSchedule = {
      studentId,
      studentName,
      batchName,
      batchId: 0, // Will be set from plan if available
      dailyClasses: {},
      todaysClasses: [],
      totalPeriodsThisWeek: 0,
      freePeriodsToday: [],
      lunchtimeSlot: 3, // Default lunch at period 4 (index 3)
    };

    if (!plan.timetable || !plan.school_profile) {
      return schedule;
    }

    const { periods_per_day } = plan.school_profile;
    let totalPeriods = 0;
    const today = new Date().getDay();
    const todayIndex = Math.max(0, Math.min(4, today - 1));

    // Iterate through timetable and extract classes for this batch
    plan.timetable.forEach((daySchedule, dayIndex) => {
      if (dayIndex >= DAYS.length) return;

      const dayName = DAYS[dayIndex];
      const periodsForDay: (StudentClass | null)[] = [];
      const freePeriodsForDay: number[] = [];

      daySchedule.forEach((slot, periodIndex) => {
        if (slot === null) {
          periodsForDay.push(null);
          freePeriodsForDay.push(periodIndex);
        } else {
          // Check if this slot belongs to the student's batch
          const slotBatch = slot.batch_name || slot.batchName;
          if (slotBatch === batchName || slotBatch?.includes(batchName)) {
            const studentClass: StudentClass = {
              periodIndex,
              subjectName: slot.subject || slot.subjectName || "Unknown",
              subjectId: slot.subject_id || slot.subjectId || 0,
              teacherName: slot.teacher || slot.teacherName || "TBA",
              teacherId: slot.teacher_id || slot.teacherId || 0,
              isCore: slot.is_core !== false,
              duration: "45 mins",
              day: dayName,
              dayIndex,
            };
            periodsForDay.push(studentClass);

            // Add to today's classes if it's today
            if (dayIndex === todayIndex) {
              schedule.todaysClasses.push(studentClass);
            }
          } else {
            periodsForDay.push(null);
          }
        }
      });

      schedule.dailyClasses[dayName] = periodsForDay;

      // Count free periods for today
      if (dayIndex === todayIndex) {
        schedule.freePeriodsToday = freePeriodsForDay;
      }

      totalPeriods += periodsForDay.filter((p) => p !== null).length;
    });

    schedule.totalPeriodsThisWeek = totalPeriods;
    return schedule;
  }, [plan, studentId, studentName, batchName]);

  const selectedDayPeriods =
    studentSchedule.dailyClasses[DAYS[selectedDay]] || [];

  const todayDate = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
          Your Timetable
        </h1>
        <p className="text-slate-600 mt-1">
          {studentName} • {batchName}
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Classes Today</p>
              <p className="text-2xl font-bold text-slate-900">
                {studentSchedule.todaysClasses.length}
              </p>
            </div>
            <BookOpen className="w-8 h-8 text-blue-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-yellow-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Free Periods</p>
              <p className="text-2xl font-bold text-slate-900">
                {studentSchedule.freePeriodsToday.length}
              </p>
            </div>
            <AlertCircle className="w-8 h-8 text-yellow-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-purple-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Week Total</p>
              <p className="text-2xl font-bold text-slate-900">
                {studentSchedule.totalPeriodsThisWeek}
              </p>
            </div>
            <Calendar className="w-8 h-8 text-purple-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-600 text-sm font-medium">Today</p>
              <p className="text-sm font-semibold text-slate-900">
                {DAYS_SHORT[selectedDay]}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-500 opacity-20" />
          </div>
        </div>
      </div>

      {/* Today's Classes Summary */}
      {studentSchedule.todaysClasses.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <h2 className="font-semibold text-slate-900 mb-4">Today's Classes</h2>
          <div className="space-y-3">
            {studentSchedule.todaysClasses.sort((a, b) => a.periodIndex - b.periodIndex).map((cls, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200"
              >
                <div className="flex-1">
                  <div className="font-semibold text-slate-900">
                    Period {cls.periodIndex + 1}: {cls.subjectName}
                  </div>
                  <div className="text-sm text-slate-600">
                    {cls.teacherName}
                  </div>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    cls.isCore
                      ? "bg-blue-100 text-blue-800"
                      : "bg-purple-100 text-purple-800"
                  }`}
                >
                  {cls.isCore ? "Core" : "Elective"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Day Selector */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="font-semibold text-slate-900 mb-4">Select Day</h2>
        <div className="grid grid-cols-5 gap-2">
          {DAYS.map((day, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedDay(idx)}
              className={`py-2 px-2 rounded-lg font-semibold transition-all ${
                selectedDay === idx
                  ? "bg-blue-500 text-white shadow-lg"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {DAYS_SHORT[idx]}
            </button>
          ))}
        </div>
      </div>

      {/* Selected Day Detailed View */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="font-semibold text-slate-900 mb-4">
          {DAYS[selectedDay]} Schedule
        </h2>

        {selectedDayPeriods.length === 0 ? (
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-600">No classes scheduled for this day</p>
          </div>
        ) : (
          <div className="space-y-3">
            {selectedDayPeriods.map((cls, idx) => {
              // Lunch period
              if (idx === 3) {
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg border-2 border-orange-300"
                  >
                    <div className="flex items-center gap-3">
                      <Clock className="w-5 h-5 text-orange-600" />
                      <div>
                        <div className="font-semibold text-orange-900">
                          Period {idx + 1}: Lunch Break
                        </div>
                        <div className="text-sm text-orange-700">12:00 - 12:45</div>
                      </div>
                    </div>
                  </div>
                );
              }

              if (cls === null) {
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg border border-yellow-200"
                  >
                    <div className="flex items-center gap-3">
                      <AlertCircle className="w-5 h-5 text-yellow-600" />
                      <div>
                        <div className="font-semibold text-yellow-900">
                          Period {idx + 1}: Free
                        </div>
                        <div className="text-sm text-yellow-700">
                          No class scheduled
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={idx}
                  className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200"
                >
                  <div className="flex-1">
                    <div className="font-semibold text-slate-900">
                      Period {cls.periodIndex + 1}: {cls.subjectName}
                    </div>
                    <div className="text-sm text-slate-600">
                      {cls.teacherName} • {cls.duration}
                    </div>
                  </div>
                  <div
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      cls.isCore
                        ? "bg-blue-200 text-blue-800"
                        : "bg-purple-200 text-purple-800"
                    }`}
                  >
                    {cls.isCore ? "Core" : "Elective"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Weekly Overview Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
        <h2 className="font-semibold text-slate-900 p-4 border-b border-slate-200">
          Weekly Overview
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-900">
                  Period
                </th>
                {DAYS.map((day, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-3 text-center font-semibold text-slate-900"
                  >
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: plan.school_profile?.periods_per_day || 6 }).map((_, periodIdx) => (
                <tr key={periodIdx} className="border-b border-slate-200">
                  <td className="px-4 py-3 font-semibold text-slate-900 bg-slate-50">
                    {periodIdx === 3 ? "🍽️ Lunch" : `P${periodIdx + 1}`}
                  </td>
                  {DAYS.map((day, dayIdx) => {
                    const cls = studentSchedule.dailyClasses[day]?.[periodIdx];
                    const cellClass =
                      periodIdx === 3
                        ? "bg-orange-50"
                        : cls === null
                        ? "bg-yellow-50"
                        : "bg-blue-50";

                    return (
                      <td
                        key={`${dayIdx}-${periodIdx}`}
                        className={`px-4 py-3 text-center border-l border-slate-200 ${cellClass}`}
                      >
                        {periodIdx === 3 ? (
                          <span className="text-xs text-orange-700 font-semibold">
                            Break
                          </span>
                        ) : cls ? (
                          <div className="text-xs">
                            <div className="font-semibold text-slate-900">
                              {cls.subjectName}
                            </div>
                            <div className="text-slate-600">
                              {cls.teacherName}
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-yellow-700 font-semibold">
                            Free
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Subject Distribution */}
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5" />
          Your Subjects This Week
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from(
            new Map(
              studentSchedule.todaysClasses
                .concat(
                  Object.values(studentSchedule.dailyClasses)
                    .flat()
                    .filter((c): c is StudentClass => c !== null)
                )
                .map((c) => [c.subjectName, c])
            ).values()
          ).map((cls, idx) => (
            <div
              key={idx}
              className="p-3 bg-slate-50 rounded-lg border border-slate-200"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-900">
                    {cls.subjectName}
                  </div>
                  <div className="text-sm text-slate-600">{cls.teacherName}</div>
                </div>
                <div
                  className={`px-2 py-1 rounded text-xs font-semibold ${
                    cls.isCore
                      ? "bg-blue-100 text-blue-800"
                      : "bg-purple-100 text-purple-800"
                  }`}
                >
                  {cls.isCore ? "Core" : "Elective"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
