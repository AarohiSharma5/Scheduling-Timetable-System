import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuthStore } from "../stores/authStore";

interface Exam {
  id: number;
  name: string;
  term: string | null;
  exam_type: string;
  max_marks: number;
  start_date: string | null;
  end_date: string | null;
  status: string;
}

interface ClassItem {
  batch_id: number;
  label: string;
  subject_ids: number[];
}

interface SubjectItem {
  id: number;
  name: string;
}

interface MarkRow {
  student_id: number;
  name: string;
  roll_no: number | null;
  marks_obtained: number | null;
  is_absent: boolean;
  grade: string | null;
}

interface ResultSubject {
  subject_id: number;
  subject: string;
  marks_obtained: number | null;
  max_marks: number;
  is_absent: boolean;
  grade: string | null;
}

interface ResultRow {
  student_id: number;
  name: string;
  roll_no: number | null;
  subjects: ResultSubject[];
  total_obtained: number | null;
  total_max: number | null;
  percentage: number | null;
  overall_grade: string | null;
  has_marks: boolean;
  rank?: number;
}

const EXAM_TYPES = [
  { value: "unit_test", label: "Unit Test" },
  { value: "mid_term", label: "Mid Term" },
  { value: "final", label: "Final" },
  { value: "other", label: "Other" },
];

const gradeColor = (g: string | null) => {
  if (!g) return "text-slate-400";
  if (g.startsWith("A")) return "text-green-700";
  if (g.startsWith("B")) return "text-emerald-600";
  if (g.startsWith("C")) return "text-amber-600";
  if (g === "D") return "text-orange-600";
  return "text-red-600";
};

export default function ExamsPanel() {
  const role = useAuthStore((s) => s.user?.role);
  const canManage = role === "admin" || role === "principal" || role === "coordinator";

  const [mode, setMode] = useState<"marks" | "results">("marks");
  const [exams, setExams] = useState<Exam[]>([]);
  const [examId, setExamId] = useState<number | "">("");
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [batchId, setBatchId] = useState<number | "">("");
  const [subjectId, setSubjectId] = useState<number | "">("");

  const [rows, setRows] = useState<MarkRow[]>([]);
  const [maxMarks, setMaxMarks] = useState<number>(100);
  const [results, setResults] = useState<{ subjects: SubjectItem[]; students: ResultRow[] } | null>(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const selectedExam = useMemo(() => exams.find((e) => e.id === examId), [exams, examId]);
  const subjectsForClass = useMemo(() => {
    const cls = classes.find((c) => c.batch_id === batchId);
    if (!cls) return subjects;
    const ids = new Set(cls.subject_ids);
    const filtered = subjects.filter((s) => ids.has(s.id));
    return filtered.length ? filtered : subjects;
  }, [classes, subjects, batchId]);

  // Initial load: exams + meta (classes + subjects)
  useEffect(() => {
    (async () => {
      try {
        const [examList, meta] = await Promise.all([api.exams.list(), api.exams.meta()]);
        setExams(examList);
        if (examList.length) setExamId(examList[0].id);
        setClasses(meta.classes);
        setSubjects(meta.subjects);
        if (meta.classes.length) setBatchId(meta.classes[0].batch_id);
      } catch (e: any) {
        setErr(e?.response?.data?.error || "Couldn't load exams.");
      }
    })();
  }, []);

  useEffect(() => {
    if (selectedExam) setMaxMarks(selectedExam.max_marks || 100);
  }, [selectedExam]);

  // Keep subject valid for the chosen class
  useEffect(() => {
    if (subjectsForClass.length && !subjectsForClass.some((s) => s.id === subjectId)) {
      setSubjectId(subjectsForClass[0].id);
    }
  }, [subjectsForClass, subjectId]);

  const loadMarksheet = async () => {
    if (examId === "" || batchId === "" || subjectId === "") return;
    try {
      setLoading(true);
      setErr("");
      setMsg("");
      const data = await api.exams.marksheet(examId as number, {
        batch_id: batchId as number,
        subject_id: subjectId as number,
      });
      setMaxMarks(data.max_marks);
      setRows(data.students);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load the marksheet.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  const loadResults = async () => {
    if (examId === "" || batchId === "") return;
    try {
      setLoading(true);
      setErr("");
      const data = await api.exams.results(examId as number, { batch_id: batchId as number });
      setResults({ subjects: data.subjects, students: data.students });
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't load results.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "marks") loadMarksheet();
    else loadResults();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, examId, batchId, subjectId]);

  const setMark = (studentId: number, value: string) => {
    setRows((rs) =>
      rs.map((r) =>
        r.student_id === studentId
          ? { ...r, marks_obtained: value === "" ? null : Number(value), is_absent: false }
          : r
      )
    );
  };

  const toggleAbsent = (studentId: number) => {
    setRows((rs) =>
      rs.map((r) =>
        r.student_id === studentId
          ? { ...r, is_absent: !r.is_absent, marks_obtained: !r.is_absent ? null : r.marks_obtained }
          : r
      )
    );
  };

  const save = async () => {
    if (examId === "" || batchId === "" || subjectId === "") return;
    const bad = rows.find(
      (r) => !r.is_absent && r.marks_obtained != null && (r.marks_obtained < 0 || r.marks_obtained > maxMarks)
    );
    if (bad) {
      setErr(`Marks must be between 0 and ${maxMarks}.`);
      return;
    }
    try {
      setSaving(true);
      setErr("");
      const res = await api.exams.saveMarks(examId as number, {
        batch_id: batchId as number,
        subject_id: subjectId as number,
        max_marks: maxMarks,
        records: rows.map((r) => ({
          student_id: r.student_id,
          marks_obtained: r.is_absent ? null : r.marks_obtained,
          is_absent: r.is_absent,
        })),
      });
      setMsg(`Saved marks for ${res.saved} student(s).`);
      await loadMarksheet();
    } catch (e: any) {
      const d = e?.response?.data;
      setErr(d?.details?.join(" ") || d?.error || "Couldn't save marks.");
    } finally {
      setSaving(false);
    }
  };

  const togglePublish = async () => {
    if (!selectedExam) return;
    try {
      const next = selectedExam.status !== "published";
      const updated = await api.exams.publish(selectedExam.id, next);
      setExams((es) => es.map((e) => (e.id === updated.id ? updated : e)));
      setMsg(next ? "Results published — students can now see them." : "Results unpublished.");
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't update publish status.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => { setMode("marks"); setMsg(""); setErr(""); }}
          className={`px-4 py-2 rounded-lg font-medium ${mode === "marks" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}
        >
          ✍️ Enter Marks
        </button>
        <button
          onClick={() => { setMode("results"); setMsg(""); setErr(""); }}
          className={`px-4 py-2 rounded-lg font-medium ${mode === "results" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}
        >
          🧾 Results / Report Card
        </button>
        {canManage && (
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="ml-auto px-4 py-2 rounded-lg font-medium bg-green-600 text-white hover:bg-green-700"
          >
            + New Exam
          </button>
        )}
      </div>

      {showCreate && canManage && (
        <CreateExamForm
          onCancel={() => setShowCreate(false)}
          onCreated={(exam) => {
            setExams((es) => [exam, ...es]);
            setExamId(exam.id);
            setShowCreate(false);
            setMsg(`Created exam "${exam.name}".`);
          }}
        />
      )}

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end bg-slate-50 border border-slate-200 rounded-lg p-4">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Exam</label>
          <select
            value={examId}
            onChange={(e) => setExamId(e.target.value ? Number(e.target.value) : "")}
            className="border rounded px-3 py-2 bg-white min-w-[12rem]"
          >
            {exams.length === 0 && <option value="">No exams yet</option>}
            {exams.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}{e.status === "draft" ? " (draft)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Class</label>
          <select
            value={batchId}
            onChange={(e) => setBatchId(e.target.value ? Number(e.target.value) : "")}
            className="border rounded px-3 py-2 bg-white min-w-[10rem]"
          >
            {classes.length === 0 && <option value="">No classes</option>}
            {classes.map((c) => (
              <option key={c.batch_id} value={c.batch_id}>{c.label}</option>
            ))}
          </select>
        </div>
        {mode === "marks" && (
          <>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Subject</label>
              <select
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value ? Number(e.target.value) : "")}
                className="border rounded px-3 py-2 bg-white min-w-[9rem]"
              >
                {subjectsForClass.length === 0 && <option value="">No subjects</option>}
                {subjectsForClass.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Max marks</label>
              <input
                type="number"
                min={1}
                value={maxMarks}
                onChange={(e) => setMaxMarks(Number(e.target.value) || 0)}
                className="border rounded px-3 py-2 bg-white w-24"
              />
            </div>
          </>
        )}
        {canManage && selectedExam && (
          <div className="ml-auto">
            <button
              onClick={togglePublish}
              className={`px-4 py-2 rounded-lg font-medium ${
                selectedExam.status === "published"
                  ? "bg-amber-100 text-amber-800 border border-amber-300"
                  : "bg-blue-600 text-white"
              }`}
            >
              {selectedExam.status === "published" ? "Published ✓ (unpublish)" : "Publish results"}
            </button>
          </div>
        )}
      </div>

      {msg && <div className="bg-green-50 border border-green-300 text-green-800 px-4 py-2 rounded-lg text-sm">{msg}</div>}
      {err && <div className="bg-red-50 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm">{err}</div>}
      {loading && <p className="text-slate-500 text-sm">⏳ Loading…</p>}

      {/* MARKS MODE */}
      {mode === "marks" && !loading && examId !== "" && (
        rows.length === 0 ? (
          <p className="text-slate-500 text-sm">No students found for this class.</p>
        ) : (
          <>
            <div className="border border-slate-200 rounded-lg divide-y">
              <div className="flex items-center gap-3 px-3 py-2 bg-slate-100 text-xs font-semibold text-slate-600">
                <span className="w-8">Roll</span>
                <span className="flex-1">Student</span>
                <span className="w-28 text-center">Marks / {maxMarks}</span>
                <span className="w-14 text-center">Grade</span>
                <span className="w-20 text-center">Absent</span>
              </div>
              {rows.map((r) => (
                <div key={r.student_id} className="flex items-center gap-3 px-3 py-2">
                  <span className="w-8 text-slate-400 text-sm">{r.roll_no ?? "—"}</span>
                  <span className="flex-1 font-medium text-slate-800">{r.name}</span>
                  <input
                    type="number"
                    min={0}
                    max={maxMarks}
                    value={r.is_absent ? "" : r.marks_obtained ?? ""}
                    disabled={r.is_absent}
                    onChange={(e) => setMark(r.student_id, e.target.value)}
                    className="w-28 border rounded px-2 py-1 text-center bg-white disabled:bg-slate-100"
                    placeholder="—"
                  />
                  <span className={`w-14 text-center font-semibold ${gradeColor(r.grade)}`}>
                    {r.is_absent ? "AB" : r.grade ?? "—"}
                  </span>
                  <span className="w-20 text-center">
                    <input
                      type="checkbox"
                      checked={r.is_absent}
                      onChange={() => toggleAbsent(r.student_id)}
                      className="h-4 w-4"
                    />
                  </span>
                </div>
              ))}
            </div>
            <button
              onClick={save}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-bold py-2.5 px-6 rounded-lg"
            >
              {saving ? "Saving…" : "Save Marks"}
            </button>
          </>
        )
      )}

      {/* RESULTS MODE */}
      {mode === "results" && !loading && results && (
        results.students.every((s) => !s.has_marks) ? (
          <p className="text-slate-500 text-sm">No marks entered yet for this class.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-100 text-left">
                  <th className="border px-2 py-2 w-12">Roll</th>
                  <th className="border px-2 py-2">Student</th>
                  {results.subjects.map((s) => (
                    <th key={s.id} className="border px-2 py-2 text-center">{s.name}</th>
                  ))}
                  <th className="border px-2 py-2 text-center">Total</th>
                  <th className="border px-2 py-2 text-center">%</th>
                  <th className="border px-2 py-2 text-center">Grade</th>
                  <th className="border px-2 py-2 text-center">Rank</th>
                </tr>
              </thead>
              <tbody>
                {results.students.map((stu) => {
                  const bySubj = new Map(stu.subjects.map((s) => [s.subject_id, s]));
                  return (
                    <tr key={stu.student_id}>
                      <td className="border px-2 py-1.5 text-slate-400">{stu.roll_no ?? "—"}</td>
                      <td className="border px-2 py-1.5 font-medium text-slate-800">{stu.name}</td>
                      {results.subjects.map((s) => {
                        const m = bySubj.get(s.id);
                        return (
                          <td key={s.id} className="border px-2 py-1.5 text-center">
                            {!m ? "—" : m.is_absent ? <span className="text-red-600">AB</span> : m.marks_obtained}
                          </td>
                        );
                      })}
                      <td className="border px-2 py-1.5 text-center text-slate-700">
                        {stu.total_obtained == null ? "—" : `${stu.total_obtained}/${stu.total_max}`}
                      </td>
                      <td className="border px-2 py-1.5 text-center font-semibold">
                        {stu.percentage == null ? "—" : `${stu.percentage}%`}
                      </td>
                      <td className={`border px-2 py-1.5 text-center font-semibold ${gradeColor(stu.overall_grade)}`}>
                        {stu.overall_grade ?? "—"}
                      </td>
                      <td className="border px-2 py-1.5 text-center text-slate-600">{stu.rank ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {selectedExam?.status !== "published" && canManage && (
              <p className="text-xs text-amber-700 mt-2">
                These results are still a draft — publish the exam to make them visible to students.
              </p>
            )}
          </div>
        )
      )}
    </div>
  );
}

function CreateExamForm({
  onCreated,
  onCancel,
}: {
  onCreated: (exam: Exam) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [examType, setExamType] = useState("unit_test");
  const [term, setTerm] = useState("");
  const [maxMarks, setMaxMarks] = useState(100);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!name.trim()) {
      setErr("Exam name is required.");
      return;
    }
    try {
      setBusy(true);
      setErr("");
      const exam = await api.exams.create({
        name: name.trim(),
        exam_type: examType,
        term: term || undefined,
        max_marks: maxMarks,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      onCreated(exam);
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Couldn't create the exam.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3 shadow-sm">
      <h3 className="font-semibold text-slate-800">New Exam</h3>
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-[14rem]">
          <label className="block text-xs font-semibold text-slate-600 mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
                 placeholder="e.g. Term 1 Mid-Term"
                 className="border rounded px-3 py-2 bg-white w-full" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Type</label>
          <select value={examType} onChange={(e) => setExamType(e.target.value)}
                  className="border rounded px-3 py-2 bg-white">
            {EXAM_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Term</label>
          <input value={term} onChange={(e) => setTerm(e.target.value)}
                 placeholder="Term 1" className="border rounded px-3 py-2 bg-white w-28" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Max marks</label>
          <input type="number" min={1} value={maxMarks}
                 onChange={(e) => setMaxMarks(Number(e.target.value) || 0)}
                 className="border rounded px-3 py-2 bg-white w-24" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">From</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                 className="border rounded px-3 py-2 bg-white" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">To</label>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                 className="border rounded px-3 py-2 bg-white" />
        </div>
      </div>
      {err && <p className="text-red-600 text-sm">{err}</p>}
      <div className="flex gap-2">
        <button onClick={submit} disabled={busy}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold py-2 px-5 rounded-lg">
          {busy ? "Creating…" : "Create Exam"}
        </button>
        <button onClick={onCancel}
                className="bg-slate-200 text-slate-700 font-semibold py-2 px-5 rounded-lg">
          Cancel
        </button>
      </div>
    </div>
  );
}
