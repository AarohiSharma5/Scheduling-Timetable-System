import React, { useState, useMemo } from "react";
import {
  Calendar,
  Clock,
  BookOpen,
  Users,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import type {
  Plan,
  ScheduleClass,
  TeacherSchedule,
} from "../types";

interface TeacherDashboardProps {
  plan: Plan;
  teacherId: number;
  teacherName: string;
}

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function TeacherDashboard({
  plan,
  teacherId,
  teacherName,
}: TeacherDashboardProps) {
  const [selectedDay, setSelectedDay] = useState<number>(
    Math.max(0, Math.min(6, new Date().getDay() - 1))
  );

  // Parse timetable data for this teacher
  const teacherSchedule = useMemo(() => {
    const schedule: TeacherSchedule = {
      teacherId,
      teacherName,
      dailyClasses: {},
      todaysClasses: [],
      totalPeriodsThisWeek: 0,
      freePeriodsToday: [],
    };

    if (!plan.timetable || !plan.school_profile) {
      return schedule;
    }

    const { periods_per_day } = plan.school_profile;
    let totalPeriods = 0;
    const todayIndex = Math.max(0, Math.min(6, new Date().getDay() - 1)); // 0 = Monday
    const todayClasses: ScheduleClass[] = [];
    const freeToday: number[] = [];

    // Initialize daily classes
    DAYS.forEach((day) => {
      schedule.dailyClasses[day] = [];
    });

    // Parse timetable for this teacher
    plan.timetable.forEach((daySchedule, dayIndex) => {
      if (dayIndex >= DAYS.length) return;

      const day = DAYS[dayIndex];
      const dayClasses: (ScheduleClass | null)[] = [];
      const freePeriods: number[] = [];

      daySchedule.forEach((slot, periodIndex) => {
        if (slot && slot.teacher_id === teacherId) {
          const subject = plan.subjects.find((s) => s.id === slot.subject_id);
          const scheduleClass: ScheduleClass = {
            periodIndex,
            subjectName: slot.subject,
            subjectId: slot.subject_id,
            batchName: "Class", // Will show batch name when batch system is integrated
            batchId: 0,
            isCore: subject?.is_core || false,
            day: day as any,
            dayIndex,
            time: `Period ${periodIndex + 1}`,
          };

          dayClasses.push(scheduleClass);
          totalPeriods++;

          if (dayIndex === todayIndex) {
            todayClasses.push(scheduleClass);
          }
        } else {
          dayClasses.push(null);
          if (dayIndex === todayIndex && !slot) {
            freePeriods.push(periodIndex);
          }
        }
      });

      schedule.dailyClasses[day] = dayClasses;
      if (dayIndex === todayIndex) {
        schedule.freePeriodsToday = freePeriods;
      }
    });

    schedule.todaysClasses = todayClasses;
    schedule.totalPeriodsThisWeek = totalPeriods;

    return schedule;
  }, [plan, teacherId]);

  const currentDayName = DAYS[selectedDay] || "Monday";
  const currentDaySchedule =
    teacherSchedule.dailyClasses[currentDayName] || [];
  const periodCount = plan.school_profile?.periods_per_day || 6;

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Today's Classes</p>
              <p className="text-3xl font-bold text-blue-900 mt-2">
                {teacherSchedule.todaysClasses.length}
              </p>
            </div>
            <Calendar className="w-12 h-12 text-blue-300" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-600 font-medium">
                Free Periods Today
              </p>
              <p className="text-3xl font-bold text-purple-900 mt-2">
                {teacherSchedule.freePeriodsToday.length}
              </p>
            </div>
            <Clock className="w-12 h-12 text-purple-300" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600 font-medium">
                Weekly Periods
              </p>
              <p className="text-3xl font-bold text-green-900 mt-2">
                {teacherSchedule.totalPeriodsThisWeek}
              </p>
            </div>
            <BookOpen className="w-12 h-12 text-green-300" />
          </div>
        </div>
      </div>

      {/* Today's Classes Summary */}
      {teacherSchedule.todaysClasses.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            Today's Classes Summary
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {teacherSchedule.todaysClasses.map((cls, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-4 bg-gradient-to-r from-green-50 to-transparent border-l-4 border-green-500 rounded-r hover:shadow-md transition-shadow"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 truncate">
                    {cls.subjectName}
                  </p>
                  <p className="text-xs text-gray-600 truncate">
                    {cls.time} • {cls.batchName}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap flex-shrink-0 ${
                    cls.isCore
                      ? "bg-blue-100 text-blue-700"
                      : "bg-purple-100 text-purple-700"
                  }`}
                >
                  {cls.isCore ? "Core" : "Elect"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily Schedule View */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">
          Daily Schedule
        </h3>

        {/* Day Selector */}
        <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
          {DAYS.map((day, idx) => {
            const isToday =
              idx === Math.max(0, Math.min(6, new Date().getDay() - 1));
            return (
              <button
                key={day}
                onClick={() => setSelectedDay(idx)}
                className={`px-4 py-2 whitespace-nowrap rounded-lg font-medium transition-all duration-200 ${
                  selectedDay === idx
                    ? "bg-blue-600 text-white shadow-md"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                } ${isToday ? "border-2 border-blue-500" : ""}`}
              >
                {day}
                {isToday && <span className="ml-2 text-xs">●</span>}
              </button>
            );
          })}
        </div>

        {/* Periods for Selected Day */}
        <div className="space-y-3">
          {currentDaySchedule.map((period, periodIdx) => (
            <div
              key={periodIdx}
              className={`flex items-stretch overflow-hidden rounded-lg border-2 transition-all hover:shadow-md ${
                period
                  ? "bg-white border-blue-200"
                  : "bg-gradient-to-r from-yellow-50 to-yellow-100 border-yellow-300"
              }`}
            >
              {/* Period Number Badge */}
              <div
                className={`w-24 flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                  period
                    ? "bg-blue-50 text-blue-700"
                    : "bg-yellow-100 text-yellow-700"
                }`}
              >
                {periodIdx + 1}
              </div>

              {/* Period Content */}
              <div className="flex-1 p-4">
                {period ? (
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">
                        {period.subjectName}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {period.batchName}
                      </p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                        period.isCore
                          ? "bg-blue-100 text-blue-700"
                          : "bg-purple-100 text-purple-700"
                      }`}
                    >
                      {period.isCore ? "Core" : "Elective"}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-yellow-700">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="font-medium">Free Period</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Full Week Grid Overview */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm overflow-x-auto">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">
          Weekly Timetable Grid
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs md:text-sm">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="text-left py-3 px-3 font-semibold text-gray-700 bg-gray-50 rounded-tl">
                  Period
                </th>
                {DAYS.map((day, idx) => {
                  const isToday = idx === new Date().getDay() - 1;
                  return (
                    <th
                      key={day}
                      className={`text-center py-3 px-2 md:px-3 font-semibold ${
                        isToday
                          ? "bg-blue-100 text-blue-700 border-b-2 border-blue-500"
                          : "bg-gray-50 text-gray-700"
                      }`}
                    >
                      <div>{DAYS_SHORT[idx]}</div>
                      {isToday && <div className="text-xs">TODAY</div>}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: periodCount }).map((_, periodIdx) => (
                <tr key={periodIdx} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="py-3 px-3 font-medium text-gray-700 bg-gray-50 rounded-l">
                    P{periodIdx + 1}
                  </td>
                  {DAYS.map((day, dayIdx) => {
                    const slot =
                      teacherSchedule.dailyClasses[day]?.[periodIdx];
                    const isToday = dayIdx === new Date().getDay() - 1;

                    return (
                      <td
                        key={`${day}-${periodIdx}`}
                        className={`py-3 px-2 md:px-3 text-center text-xs md:text-sm ${
                          slot
                            ? isToday
                              ? "bg-blue-100 border-l-4 border-blue-600"
                              : "bg-blue-50 border-l-4 border-blue-300"
                            : isToday
                            ? "bg-yellow-100 border-l-4 border-yellow-400"
                            : "bg-gray-50"
                        }`}
                      >
                        {slot ? (
                          <div className="space-y-1">
                            <p className="font-semibold text-gray-900 truncate">
                              {slot.subjectName}
                            </p>
                            <p className="text-xs text-gray-600 truncate">
                              {slot.batchName}
                            </p>
                            <span
                              className={`inline-block text-xs font-semibold px-1.5 py-0.5 rounded ${
                                slot.isCore
                                  ? "bg-blue-200 text-blue-700"
                                  : "bg-purple-200 text-purple-700"
                              }`}
                            >
                              {slot.isCore ? "C" : "E"}
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-400 font-semibold">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="mt-6 pt-6 border-t border-gray-200 flex flex-wrap gap-6 text-xs md:text-sm">
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-blue-100 border-2 border-blue-300 rounded"></span>
            <span className="text-gray-600">Your Class</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block w-4 h-4 bg-yellow-100 border-2 border-yellow-300 rounded"></span>
            <span className="text-gray-600">Free Period</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded">
              C
            </span>
            <span className="text-gray-600">Core Subject</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-semibold rounded">
              E
            </span>
            <span className="text-gray-600">Elective Subject</span>
          </div>
        </div>
      </div>

      {/* Analytics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Schedule Breakdown */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Schedule Breakdown
          </h3>
          <div className="space-y-3">
            {DAYS.map((day, idx) => {
              const daySchedule = teacherSchedule.dailyClasses[day] || [];
              const classCount = daySchedule.filter((p) => p !== null).length;
              const freeCount = daySchedule.filter((p) => p === null).length;

              return (
                <div key={day} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <p className="font-medium text-gray-900">{day}</p>
                    <span className="text-xs text-gray-600">
                      {classCount}/{daySchedule.length} periods
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{
                        width: `${((classCount / daySchedule.length) * 100) || 0}%`,
                      }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Subject Distribution */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Subject Distribution
          </h3>
          <div className="space-y-3">
            {Array.from(
              new Map(
                teacherSchedule.todaysClasses.map((cls) => [
                  cls.subjectId,
                  { name: cls.subjectName, isCore: cls.isCore },
                ])
              ).values()
            ).map((subject, idx) => {
              const count = teacherSchedule.todaysClasses.filter(
                (cls) => cls.subjectName === subject.name
              ).length;

              return (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                          subject.isCore
                            ? "bg-blue-100 text-blue-700"
                            : "bg-purple-100 text-purple-700"
                        }`}
                      >
                        {subject.isCore ? "Core" : "Elect"}
                      </span>
                      <p className="font-medium text-gray-900">
                        {subject.name}
                      </p>
                    </div>
                    <span className="text-sm font-semibold text-gray-700">
                      {count}x
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
