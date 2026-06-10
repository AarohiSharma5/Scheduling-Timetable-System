import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import TimetableEditor from "./TimetableEditor";
import FeasibilityPanel from "./FeasibilityPanel";

interface GenerationStatus {
  status: "idle" | "loading" | "success" | "error" | "warning";
  message: string;
  details?: string[];
}

interface TimetableSummary {
  id: number;
  name: string;
  status?: string;
}

interface BatchSummary {
  id: number;
  grade: string;
  section: string;
  student_count?: number;
  display_name?: string;
}

interface TeacherSummary {
  id: number;
  name: string;
  teacher_code?: string | null;
}

type ExportMode = "batch" | "teacher";

export default function TimetableGenerator() {
  const [status, setStatus] = useState<GenerationStatus>({ status: "idle", message: "" });

  const [timetables, setTimetables] = useState<TimetableSummary[]>([]);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [teachers, setTeachers] = useState<TeacherSummary[]>([]);
  const [subjectCount, setSubjectCount] = useState<number>(0);

  const [selectedTimetable, setSelectedTimetable] = useState<number | "">("");
  const [showEditor, setShowEditor] = useState(false);
  const [exportMode, setExportMode] = useState<ExportMode>("batch");
  // "all" or a specific batch/teacher id (as string for the <select>).
  const [selectedTarget, setSelectedTarget] = useState<string>("all");

  const loadData = async () => {
    try {
      const [ttRes, batchRes, teacherRes, subjectRes] = await Promise.allSettled([
        api.timetable.list(),
        api.admin.batches.list(),
        api.admin.teachers.list(),
        api.admin.subjects.list(),
      ]);

      if (ttRes.status === "fulfilled") {
        // /timetable/list returns { timetables: [...] }; tolerate a bare array too.
        const raw: any = ttRes.value;
        const list: TimetableSummary[] = Array.isArray(raw) ? raw : raw?.timetables || [];
        setTimetables(list);
        // Always make sure a valid timetable is selected after (re)login. If the
        // current selection is empty or no longer exists, fall back to the most
        // recent one — preferring a published version, else the newest draft.
        const stillValid = list.some((t) => t.id === selectedTimetable);
        if (list.length && !stillValid) {
          const published = list.find((t) => t.status === "published");
          setSelectedTimetable((published || list[0]).id);
        }
      }
      if (batchRes.status === "fulfilled") setBatches(batchRes.value || []);
      if (teacherRes.status === "fulfilled") setTeachers(teacherRes.value || []);
      if (subjectRes.status === "fulfilled") setSubjectCount((subjectRes.value || []).length);
    } catch {
      /* lists are best-effort; UI still works with empty selectors */
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset the target when switching between class/teacher mode.
  useEffect(() => {
    setSelectedTarget("all");
  }, [exportMode]);

  const studentTotal = useMemo(
    () => batches.reduce((sum, b) => sum + (b.student_count || 0), 0),
    [batches]
  );

  // Render the final result payload (shape is identical for sync + async paths).
  const applyGenerationResult = async (result: any) => {
    if (!result || !result.success) {
      setStatus({ status: "error", message: `Error: ${result?.message || "Generation failed"}` });
      return;
    }
    const report = result.report || {};
    const isComplete = result.complete !== false && report.complete !== false;
    if (isComplete) {
      setStatus({
        status: "success",
        message: `Timetable generated successfully! (${result.slots_generated} periods created)`,
      });
    } else {
      const shortfalls = (report.shortfalls || []) as Array<{
        subject: string; batch: string; placed: number; required: number; missing: number;
      }>;
      setStatus({
        status: "warning",
        message:
          `Timetable generated with ${report.total_required_missing || 0} required ` +
          `period(s) that couldn't be placed. Empty slots were filled with supervised ` +
          `activities — review the gaps below or adjust teachers/availability.`,
        details: shortfalls.map(
          (s) => `${s.subject} · ${s.batch}: ${s.placed}/${s.required} placed (${s.missing} missing)`
        ),
      });
    }
    await loadData();
  };

  // Poll a queued job until it finishes (or times out), then render the result.
  const pollJob = async (jobId: number) => {
    const startedAt = Date.now();
    const TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
    while (Date.now() - startedAt < TIMEOUT_MS) {
      await new Promise((r) => setTimeout(r, 2000));
      let job: any;
      try {
        job = await api.timetable.job(jobId);
      } catch {
        continue; // transient; keep polling
      }
      if (job.status === "completed") {
        await applyGenerationResult(job.result);
        return;
      }
      if (job.status === "failed") {
        setStatus({ status: "error", message: `Error: ${job.error || "Generation failed"}` });
        return;
      }
      setStatus({
        status: "loading",
        message: job.status === "running" ? "Generating timetable…" : "Queued — waiting for a worker…",
      });
    }
    setStatus({
      status: "error",
      message: "Generation is taking longer than expected. Please check back shortly.",
    });
  };

  const generateTimetable = async () => {
    try {
      setStatus({ status: "loading", message: "Generating timetable..." });

      const response = await api.post("/timetable/generate", {
        name: `Timetable ${new Date().toLocaleString()}`,
        description: "Auto-generated",
      });

      // 202 + queued: generation runs on a background worker; poll for the result.
      if (response.status === 202 || response.data?.queued) {
        setStatus({ status: "loading", message: "Queued — waiting for a worker…" });
        await pollJob(response.data.job_id);
        return;
      }

      // 201: synchronous fallback returned the full result inline.
      await applyGenerationResult(response.data);
    } catch (error: any) {
      setStatus({
        status: "error",
        message: `Error: ${error.response?.data?.error || error.response?.data?.message || error.message}`,
      });
    }
  };

  const handleExport = async () => {
    if (selectedTimetable === "") {
      setStatus({ status: "error", message: "Please generate or select a timetable first." });
      return;
    }
    try {
      const targetLabel =
        selectedTarget === "all"
          ? exportMode === "batch"
            ? "all classes"
            : "all teachers"
          : exportMode === "batch"
          ? batches.find((b) => String(b.id) === selectedTarget)?.display_name || "class"
          : teachers.find((t) => String(t.id) === selectedTarget)?.name || "teacher";

      setStatus({ status: "loading", message: `Downloading timetable for ${targetLabel}...` });

      const base = `/export/timetable/${exportMode}/${selectedTimetable}`;
      const query =
        selectedTarget === "all"
          ? ""
          : exportMode === "batch"
          ? `?batch_id=${selectedTarget}`
          : `?teacher_id=${selectedTarget}`;

      const response = await api.get(base + query, { responseType: "blob" });

      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      const fileTarget = selectedTarget === "all" ? `all-${exportMode}s` : `${exportMode}-${selectedTarget}`;
      link.setAttribute("download", `timetable_${fileTarget}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      setStatus({ status: "success", message: `Timetable downloaded for ${targetLabel}.` });
    } catch (error: any) {
      // Error bodies come back as a Blob when responseType is blob.
      let message = error.message;
      const blob = error.response?.data;
      if (blob instanceof Blob) {
        try {
          const text = await blob.text();
          message = JSON.parse(text).error || message;
        } catch {
          /* keep default */
        }
      }
      setStatus({ status: "error", message: `Error: ${message}` });
    }
  };

  const statusClasses =
    status.status === "success"
      ? "bg-green-100 text-green-800 border border-green-300"
      : status.status === "error"
      ? "bg-red-100 text-red-800 border border-red-300"
      : status.status === "warning"
      ? "bg-amber-100 text-amber-900 border border-amber-300"
      : "bg-blue-100 text-blue-800 border border-blue-300";

  return (
    <div className="space-y-6">
      {/* Pre-flight feasibility check */}
      <FeasibilityPanel />

      {/* Generate Timetable Section */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
        <h2 className="text-2xl font-bold text-blue-900 mb-2">Generate Timetable</h2>
        <p className="text-blue-700 mb-4">Create an automated timetable for all classes and teachers</p>

        <button
          onClick={generateTimetable}
          disabled={status.status === "loading"}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center gap-2"
        >
          {status.status === "loading" ? "Working..." : "Generate Timetable"}
        </button>

        {status.message && (
          <div className={`mt-4 p-3 rounded text-sm font-medium ${statusClasses}`}>
            <div>{status.message}</div>
            {status.details && status.details.length > 0 && (
              <ul className="mt-2 list-disc list-inside space-y-1 font-normal">
                {status.details.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Export Timetables Section */}
      <div className="bg-gradient-to-r from-indigo-50 to-indigo-100 rounded-lg p-6 border-2 border-indigo-200">
        <h2 className="text-2xl font-bold text-indigo-900 mb-2">Download Timetable</h2>
        <p className="text-indigo-700 mb-4">
          Choose a timetable, then download it class-wise or teacher-wise — for everyone or a specific
          class/teacher.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Timetable selector */}
          <div>
            <label className="block text-sm font-semibold text-indigo-900 mb-1">Timetable</label>
            <select
              value={selectedTimetable}
              onChange={(e) => setSelectedTimetable(e.target.value ? Number(e.target.value) : "")}
              className="w-full border border-indigo-300 rounded px-3 py-2 bg-white"
            >
              {timetables.length === 0 && <option value="">No timetables yet</option>}
              {timetables.map((tt) => (
                <option key={tt.id} value={tt.id}>
                  {tt.name}
                  {tt.status ? ` (${tt.status})` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Mode selector */}
          <div>
            <label className="block text-sm font-semibold text-indigo-900 mb-1">Download by</label>
            <select
              value={exportMode}
              onChange={(e) => setExportMode(e.target.value as ExportMode)}
              className="w-full border border-indigo-300 rounded px-3 py-2 bg-white"
            >
              <option value="batch">Class-wise</option>
              <option value="teacher">Teacher-wise</option>
            </select>
          </div>

          {/* Target selector */}
          <div>
            <label className="block text-sm font-semibold text-indigo-900 mb-1">
              {exportMode === "batch" ? "Class" : "Teacher"}
            </label>
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="w-full border border-indigo-300 rounded px-3 py-2 bg-white"
            >
              <option value="all">{exportMode === "batch" ? "All classes" : "All teachers"}</option>
              {exportMode === "batch"
                ? batches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.display_name || `Grade ${b.grade} - ${b.section}`}
                    </option>
                  ))
                : teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.teacher_code ? `${t.teacher_code} — ${t.name}` : t.name}
                    </option>
                  ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleExport}
            disabled={status.status === "loading" || selectedTimetable === ""}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed font-semibold py-2.5 px-4 rounded transition"
          >
            Download PDF
          </button>
          <button
            onClick={() => setShowEditor(true)}
            disabled={selectedTimetable === ""}
            className="flex-1 bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-300 disabled:bg-slate-100 disabled:text-slate-400 disabled:border-slate-200 disabled:cursor-not-allowed font-semibold py-2.5 px-4 rounded transition"
          >
            ✏️ Edit timetable
          </button>
        </div>
      </div>

      {showEditor && selectedTimetable !== "" && (
        <TimetableEditor
          timetableId={selectedTimetable as number}
          onClose={() => setShowEditor(false)}
          onSaved={(newId) => {
            setShowEditor(false);
            loadData().then(() => { if (newId) setSelectedTimetable(newId); });
            setStatus({ status: "success", message: "Saved manual edits as a new draft version." });
          }}
        />
      )}

      {/* Statistics */}
      <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Timetable Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-100">
            <p className="text-2xl font-bold text-blue-700">{batches.length}</p>
            <p className="text-sm text-slate-600">Classes</p>
          </div>
          <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 p-4 rounded-lg border border-indigo-100">
            <p className="text-2xl font-bold text-indigo-700">{teachers.length}</p>
            <p className="text-sm text-slate-600">Teachers</p>
          </div>
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-4 rounded-lg border border-emerald-100">
            <p className="text-2xl font-bold text-emerald-700">{studentTotal.toLocaleString()}</p>
            <p className="text-sm text-slate-600">Students</p>
          </div>
          <div className="bg-gradient-to-br from-amber-50 to-amber-100 p-4 rounded-lg border border-amber-100">
            <p className="text-2xl font-bold text-amber-700">{subjectCount}</p>
            <p className="text-sm text-slate-600">Subjects</p>
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
        <h3 className="font-bold text-amber-900 mb-2">How to Use</h3>
        <ol className="text-sm text-amber-800 space-y-1 list-decimal list-inside">
          <li>Click "Generate Timetable" to create an automated schedule</li>
          <li>Pick a timetable, choose class-wise or teacher-wise, and select a specific class/teacher or all</li>
          <li>Click "Download PDF" — it is ready to print and distribute</li>
        </ol>
      </div>
    </div>
  );
}
