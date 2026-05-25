import React, { useState, useEffect } from "react";
import { api } from "../api";
import { AlertCircle, CheckCircle, AlertTriangle, AlertOctagon } from "lucide-react";

interface ValidationReport {
  is_valid: boolean;
  errors: Array<{
    type: string;
    message: string;
    details: Record<string, any>;
  }>;
  warnings: Array<{
    type: string;
    message: string;
    details: Record<string, any>;
  }>;
  gaps: Array<{
    subject: string;
    batch_id: number;
    batch_name: string;
    periods_missing: number;
  }>;
  stats: {
    total_slots: number;
    scheduled_slots: number;
    empty_slots: number;
    teachers_affected: number;
    batches_affected: number;
  };
  summary: {
    total_errors: number;
    total_warnings: number;
    total_gaps: number;
    conflict_free: boolean;
  };
}

interface TimetableValidationProps {
  timetableId: number;
  onValidationComplete?: (report: ValidationReport) => void;
}

export default function TimetableValidation({ timetableId, onValidationComplete }: TimetableValidationProps) {
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  useEffect(() => {
    validateTimetable();
  }, [timetableId]);

  const validateTimetable = async () => {
    try {
      setLoading(true);
      setError("");
      const result = await api.timetable.validate(timetableId);
      setReport(result);
      onValidationComplete?.(result);
    } catch (err) {
      setError("Failed to validate timetable");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (section: string) => {
    const newSections = new Set(expandedSections);
    if (newSections.has(section)) {
      newSections.delete(section);
    } else {
      newSections.add(section);
    }
    setExpandedSections(newSections);
  };

  if (loading) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
        <div className="inline-block animate-spin mb-3">⏳</div>
        <p className="text-blue-800 font-medium">Validating timetable...</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-gray-100 border border-gray-300 rounded-lg p-6 text-center">
        <p className="text-gray-600">No validation data available</p>
        <button
          onClick={validateTimetable}
          className="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          Validate Now
        </button>
      </div>
    );
  }

  const healthColor =
    report.summary.total_errors === 0 && report.summary.total_warnings === 0
      ? "green"
      : report.summary.total_errors === 0
      ? "yellow"
      : "red";

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className={`border-l-4 ${
        healthColor === "green"
          ? "border-green-500 bg-green-50"
          : healthColor === "yellow"
          ? "border-yellow-500 bg-yellow-50"
          : "border-red-500 bg-red-50"
      } p-6 rounded-lg`}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {report.is_valid ? (
              <CheckCircle className={`w-8 h-8 text-green-600`} />
            ) : (
              <AlertOctagon className={`w-8 h-8 ${healthColor === "red" ? "text-red-600" : "text-yellow-600"}`} />
            )}
            <div>
              <h3 className="text-lg font-bold">
                {report.is_valid ? "✅ Timetable Valid" : "⚠️ Conflicts Detected"}
              </h3>
              <p className="text-sm">
                {report.summary.total_errors} errors • {report.summary.total_warnings} warnings •{" "}
                {report.summary.total_gaps} incomplete subjects
              </p>
            </div>
          </div>
          <button
            onClick={validateTimetable}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
          >
            Re-validate
          </button>
        </div>
      </div>

      {/* STATS */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <div className="text-sm text-blue-700 font-semibold">Total Slots</div>
          <div className="text-2xl font-bold text-blue-900">{report.stats.total_slots}</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <div className="text-sm text-green-700 font-semibold">Scheduled</div>
          <div className="text-2xl font-bold text-green-900">{report.stats.scheduled_slots}</div>
        </div>
        <div className="bg-orange-50 p-4 rounded-lg border border-orange-100">
          <div className="text-sm text-orange-700 font-semibold">Empty</div>
          <div className="text-2xl font-bold text-orange-900">{report.stats.empty_slots}</div>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-100">
          <div className="text-sm text-red-700 font-semibold">Affected Teachers</div>
          <div className="text-2xl font-bold text-red-900">{report.stats.teachers_affected}</div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
          <div className="text-sm text-purple-700 font-semibold">Affected Batches</div>
          <div className="text-2xl font-bold text-purple-900">{report.stats.batches_affected}</div>
        </div>
      </div>

      {/* CRITICAL ERRORS */}
      {report.errors.length > 0 && (
        <div className="border border-red-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection("errors")}
            className="w-full bg-red-100 hover:bg-red-150 px-6 py-4 flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="font-bold text-red-900">Critical Errors ({report.errors.length})</span>
            </div>
            <span className="text-red-700">{expandedSections.has("errors") ? "▼" : "▶"}</span>
          </button>
          {expandedSections.has("errors") && (
            <div className="bg-white divide-y">
              {report.errors.map((error, idx) => (
                <div key={idx} className="p-4">
                  <div className="font-semibold text-red-700">{error.type}</div>
                  <p className="text-gray-800 mt-1">{error.message}</p>
                  {Object.keys(error.details).length > 0 && (
                    <pre className="bg-gray-100 p-3 rounded mt-2 text-xs text-gray-700 overflow-auto">
                      {JSON.stringify(error.details, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* WARNINGS */}
      {report.warnings.length > 0 && (
        <div className="border border-yellow-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection("warnings")}
            className="w-full bg-yellow-100 hover:bg-yellow-150 px-6 py-4 flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-700" />
              <span className="font-bold text-yellow-900">Warnings ({report.warnings.length})</span>
            </div>
            <span className="text-yellow-700">{expandedSections.has("warnings") ? "▼" : "▶"}</span>
          </button>
          {expandedSections.has("warnings") && (
            <div className="bg-white divide-y">
              {report.warnings.map((warning, idx) => (
                <div key={idx} className="p-4">
                  <div className="font-semibold text-yellow-700">{warning.type}</div>
                  <p className="text-gray-800 mt-1">{warning.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* INCOMPLETE SUBJECTS (GAPS) */}
      {report.gaps.length > 0 && (
        <div className="border border-orange-200 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection("gaps")}
            className="w-full bg-orange-100 hover:bg-orange-150 px-6 py-4 flex items-center justify-between cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-orange-700" />
              <span className="font-bold text-orange-900">Incomplete Subjects ({report.gaps.length})</span>
            </div>
            <span className="text-orange-700">{expandedSections.has("gaps") ? "▼" : "▶"}</span>
          </button>
          {expandedSections.has("gaps") && (
            <div className="bg-white">
              <table className="w-full">
                <thead className="bg-orange-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-sm font-semibold">Subject</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold">Class</th>
                    <th className="px-4 py-2 text-left text-sm font-semibold">Missing Periods</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {report.gaps.map((gap, idx) => (
                    <tr key={idx}>
                      <td className="px-4 py-2">{gap.subject}</td>
                      <td className="px-4 py-2">{gap.batch_name}</td>
                      <td className="px-4 py-2">
                        <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-sm font-semibold">
                          {gap.periods_missing}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SUCCESS MESSAGE */}
      {report.is_valid && (
        <div className="bg-green-50 border border-green-300 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
            <div>
              <h4 className="font-bold text-green-900">No Conflicts Found!</h4>
              <p className="text-green-800 text-sm mt-1">
                Your timetable is valid and ready to publish. {report.stats.scheduled_slots} periods are scheduled.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
