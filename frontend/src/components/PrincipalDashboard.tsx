import React, { useState, useMemo } from "react";
import {
  BarChart3,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Users,
  BookOpen,
  Zap,
  TrendingDown,
} from "lucide-react";
import type { TimetableAnalytics, TeacherAnalytics, BatchCompletion } from "../types";

interface PrincipalDashboardProps {
  analytics: TimetableAnalytics;
  onRefresh?: () => void;
}

export default function PrincipalDashboard({
  analytics,
  onRefresh,
}: PrincipalDashboardProps) {
  const [expandedTeacher, setExpandedTeacher] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<"workload" | "name">("workload");

  // Sort teachers by workload or name
  const sortedTeachers = useMemo(() => {
    const sorted = [...analytics.teacherAnalytics];
    if (sortBy === "workload") {
      return sorted.sort((a, b) => b.workloadPercentage - a.workloadPercentage);
    } else {
      return sorted.sort((a, b) => a.teacherName.localeCompare(b.teacherName));
    }
  }, [analytics.teacherAnalytics, sortBy]);

  // Get color for workload percentage
  const getWorkloadColor = (percentage: number) => {
    if (percentage >= 90) return "text-red-600";
    if (percentage >= 75) return "text-orange-600";
    if (percentage >= 50) return "text-yellow-600";
    return "text-green-600";
  };

  const getWorkloadBgColor = (percentage: number) => {
    if (percentage >= 90) return "bg-red-50";
    if (percentage >= 75) return "bg-orange-50";
    if (percentage >= 50) return "bg-yellow-50";
    return "bg-green-50";
  };

  const getCompletionColor = (percentage: number) => {
    if (percentage >= 80) return "text-green-600";
    if (percentage >= 60) return "text-yellow-600";
    return "text-orange-600";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-8 h-8 text-indigo-600" />
            Principal Dashboard
          </h1>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-semibold"
            >
              Refresh Analytics
            </button>
          )}
        </div>
        <p className="text-slate-600">
          School Timetable Analytics & Workload Management
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-indigo-500">
          <p className="text-slate-600 text-sm font-medium">Total Teachers</p>
          <p className="text-3xl font-bold text-slate-900">
            {analytics.totalTeachers}
          </p>
          <p className="text-xs text-slate-500 mt-1">Active in schedule</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-blue-500">
          <p className="text-slate-600 text-sm font-medium">Total Batches</p>
          <p className="text-3xl font-bold text-slate-900">
            {analytics.totalBatches}
          </p>
          <p className="text-xs text-slate-500 mt-1">Classes managed</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-green-500">
          <p className="text-slate-600 text-sm font-medium">Occupancy Rate</p>
          <p className={`text-3xl font-bold ${getCompletionColor(analytics.occupancyPercentage)}`}>
            {analytics.occupancyPercentage}%
          </p>
          <p className="text-xs text-slate-500 mt-1">Period utilization</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-purple-500">
          <p className="text-slate-600 text-sm font-medium">Avg Workload</p>
          <p className="text-3xl font-bold text-slate-900">
            {analytics.averageTeacherWorkload.toFixed(0)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">Per teacher</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-4 border-l-4 border-orange-500">
          <p className="text-slate-600 text-sm font-medium">Completion</p>
          <p className={`text-3xl font-bold ${getCompletionColor(analytics.averageBatchCompletion)}`}>
            {analytics.averageBatchCompletion}%
          </p>
          <p className="text-xs text-slate-500 mt-1">Avg per batch</p>
        </div>
      </div>

      {/* Alerts & Warnings */}
      {(analytics.warnings.length > 0 || analytics.conflictCount > 0 || analytics.freeSlots > 0) && (
        <div className="bg-white rounded-lg shadow-md p-4 mb-6 border-l-4 border-amber-500">
          <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            Alerts & Notices
          </h2>
          <div className="space-y-2">
            {analytics.warnings.map((warning, idx) => (
              <div key={idx} className="flex items-start gap-2 p-2 bg-amber-50 rounded">
                <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-amber-800">{warning}</p>
              </div>
            ))}
            {analytics.conflictCount > 0 && (
              <div className="flex items-start gap-2 p-2 bg-red-50 rounded">
                <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-800">
                  {analytics.conflictCount} scheduling conflicts detected
                </p>
              </div>
            )}
            {analytics.freeSlots > 0 && (
              <div className="flex items-start gap-2 p-2 bg-yellow-50 rounded">
                <Zap className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-yellow-800">
                  {analytics.freeSlots} unassigned periods available
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Teacher Workload Analysis */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
            <Users className="w-6 h-6 text-indigo-600" />
            Teacher Workload Analysis
          </h2>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "workload" | "name")}
            className="px-3 py-1 border border-slate-300 rounded-lg text-sm bg-white"
          >
            <option value="workload">Sort by Workload</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>

        <div className="space-y-3">
          {sortedTeachers.map((teacher, idx) => (
            <div
              key={idx}
              onClick={() =>
                setExpandedTeacher(expandedTeacher === idx ? null : idx)
              }
              className={`cursor-pointer p-4 rounded-lg border transition-all ${
                expandedTeacher === idx
                  ? `${getWorkloadBgColor(teacher.workloadPercentage)} border-slate-300`
                  : "bg-slate-50 border-slate-200 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-slate-900">
                    {teacher.teacherName}
                  </h3>
                  <p className="text-sm text-slate-600">{teacher.subjectName}</p>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div
                      className={`text-2xl font-bold ${getWorkloadColor(
                        teacher.workloadPercentage
                      )}`}
                    >
                      {teacher.workloadPercentage}%
                    </div>
                    <p className="text-xs text-slate-600">Workload</p>
                  </div>

                  <div className="text-right">
                    <div className="text-lg font-bold text-slate-900">
                      {teacher.totalPeriodsAssigned}/
                      {teacher.maxPeriodsCapacity}
                    </div>
                    <p className="text-xs text-slate-600">Periods</p>
                  </div>

                  <div className="text-right">
                    <div className="text-lg font-bold text-slate-900">
                      {teacher.assignedBatches}
                    </div>
                    <p className="text-xs text-slate-600">Batches</p>
                  </div>
                </div>
              </div>

              {/* Expandable Details */}
              {expandedTeacher === idx && (
                <div className="mt-4 pt-4 border-t border-current border-opacity-20">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-semibold text-slate-600 uppercase">
                        Status
                      </p>
                      <p className="text-sm text-slate-900 mt-1">
                        {teacher.workloadPercentage >= 90
                          ? "⚠️ Overloaded"
                          : teacher.workloadPercentage >= 75
                          ? "⚡ High"
                          : teacher.workloadPercentage >= 50
                          ? "✅ Balanced"
                          : "📊 Light"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-600 uppercase">
                        Special Duties
                      </p>
                      <p className="text-sm text-slate-900 mt-1">
                        {teacher.hasSpecialDuties ? "Yes ✓" : "No"}
                      </p>
                    </div>
                  </div>

                  {/* Workload Progress Bar */}
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-slate-600 uppercase mb-2">
                      Workload Distribution
                    </p>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          teacher.workloadPercentage >= 90
                            ? "bg-red-500"
                            : teacher.workloadPercentage >= 75
                            ? "bg-orange-500"
                            : teacher.workloadPercentage >= 50
                            ? "bg-yellow-500"
                            : "bg-green-500"
                        }`}
                        style={{
                          width: `${Math.min(100, teacher.workloadPercentage)}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Batch Completion Status */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-600" />
          Batch Timetable Completion
        </h2>

        <div className="space-y-3">
          {analytics.batchCompletion.map((batch, idx) => (
            <div
              key={idx}
              className="p-4 bg-slate-50 rounded-lg border border-slate-200"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-900">
                    {batch.batchName}
                  </h3>
                  <p className="text-sm text-slate-600">
                    {batch.studentCount} students
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={`text-2xl font-bold ${getCompletionColor(
                      batch.completionPercentage
                    )}`}
                  >
                    {batch.completionPercentage}%
                  </p>
                  <p className="text-xs text-slate-600">
                    {batch.slotsFilled}/{batch.totalSlotsAvailable} slots
                  </p>
                </div>
              </div>

              {/* Completion Progress Bar */}
              <div className="w-full bg-slate-300 rounded-full h-2 mb-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    batch.completionPercentage >= 80
                      ? "bg-green-500"
                      : batch.completionPercentage >= 60
                      ? "bg-yellow-500"
                      : "bg-orange-500"
                  }`}
                  style={{ width: `${batch.completionPercentage}%` }}
                ></div>
              </div>

              {/* Missing Subjects if any */}
              {batch.missingSubjects.length > 0 && (
                <div className="pt-2 border-t border-slate-300">
                  <p className="text-xs font-semibold text-slate-600 uppercase mb-1">
                    Missing Subjects
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {batch.missingSubjects.map((subject, sidx) => (
                      <span
                        key={sidx}
                        className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded"
                      >
                        {subject}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Subject Assignment Status */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-purple-600" />
          Subject Assignment Status
        </h2>

        <div className="space-y-3">
          {analytics.subjectAssignments.map((subject, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg border ${
                subject.isFullyAssigned
                  ? "bg-green-50 border-green-200"
                  : "bg-yellow-50 border-yellow-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-900">
                      {subject.subjectName}
                    </h3>
                    {subject.isFullyAssigned ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-yellow-600" />
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mt-1">
                    {subject.assignedTeachers} teacher
                    {subject.assignedTeachers !== 1 ? "s" : ""} assigned • Needed in:{" "}
                    {subject.batchesNeedingIt.join(", ")}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-lg font-bold text-slate-900">
                    {subject.periodsAssigned}/{subject.periodsRequired}
                  </p>
                  <p className="text-xs text-slate-600">Periods</p>
                </div>
              </div>

              {/* Assignment Progress Bar */}
              <div className="mt-2 w-full bg-slate-300 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    subject.isFullyAssigned ? "bg-green-500" : "bg-yellow-500"
                  }`}
                  style={{
                    width: `${Math.min(100, (subject.periodsAssigned / subject.periodsRequired) * 100)}%`,
                  }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
