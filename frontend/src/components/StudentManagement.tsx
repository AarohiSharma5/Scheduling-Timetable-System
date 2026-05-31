import React, { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "../api";
import ImportWizard from "./ImportWizard";

interface Student {
  id: number;
  student_id: string;
  admission_no: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email?: string | null;
  class_grade: string;
  section: string;
  roll_no: number | null;
  gender?: string | null;
  date_of_birth?: string | null;
  father_name?: string | null;
  mother_name?: string | null;
  contact_number?: string | null;
  address?: string | null;
  blood_group?: string | null;
  admission_date?: string | null;
  status: string;
}

const BLOOD_GROUPS = ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"];
const GENDERS = ["", "Male", "Female", "Other"];

interface Batch {
  id: number;
  grade: string;
  section: string;
}

interface Props {
  // When provided, the component locks to one class+section (class-teacher mode)
  // and hides cross-class controls. Admin/principal leave these undefined.
  scopedGrade?: string;
  scopedSection?: string;
}

const STATUSES = ["Active", "Inactive", "Left"];

const emptyForm = {
  full_name: "",
  admission_number: "", // blank => auto-generate continuing the org's pattern
  roll_no: "", // blank => auto roll number
  class_grade: "",
  section: "", // "" => auto-balance into the lowest-strength section
  date_of_birth: "",
  gender: "",
  father_name: "",
  mother_name: "",
  email: "",
  phone: "",
  address: "",
  blood_group: "",
  joining_date: "",
  status: "Active",
};

export default function StudentManagement({ scopedGrade, scopedSection }: Props) {
  const scoped = !!scopedGrade;
  const [students, setStudents] = useState<Student[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [strengths, setStrengths] = useState<Record<string, number>>({});
  const [capacity, setCapacity] = useState(45);

  const [selectedClass, setSelectedClass] = useState(scopedGrade || "");
  const [selectedSection, setSelectedSection] = useState(scopedSection || "");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({ ...emptyForm });
  const [transferStudent, setTransferStudent] = useState<Student | null>(null);
  const [transferSection, setTransferSection] = useState("");
  const [showImport, setShowImport] = useState(false);

  const flash = (kind: "ok" | "err", text: string) => {
    setMessage({ kind, text });
    window.setTimeout(() => setMessage(null), 4000);
  };

  // Derived class/section option lists (from batches, admin mode only).
  const classes = useMemo(() => {
    const set = Array.from(new Set(batches.map((b) => b.grade)));
    return set.sort((a, b) => {
      const na = Number(a), nb = Number(b);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      if (!isNaN(na)) return -1;
      if (!isNaN(nb)) return 1;
      return a.localeCompare(b);
    });
  }, [batches]);

  const sectionsForClass = useCallback(
    (grade: string) =>
      Array.from(new Set(batches.filter((b) => b.grade === grade).map((b) => b.section))).sort(),
    [batches]
  );

  // Load batches (admin/principal only — class teachers don't have access).
  useEffect(() => {
    if (scoped) return;
    (async () => {
      try {
        const res = await api.admin.batches.list();
        const list: Batch[] = Array.isArray(res) ? res : res.data || [];
        setBatches(list);
        if (!selectedClass && list.length) {
          const grades = Array.from(new Set(list.map((b) => b.grade)));
          setSelectedClass(grades[0]);
        }
      } catch {
        /* non-fatal */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoped]);

  const fetchStudents = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (scoped) {
        params.class_grade = scopedGrade;
        params.section = scopedSection;
      } else {
        if (selectedClass) params.class_grade = selectedClass;
        if (selectedSection) params.section = selectedSection;
      }
      if (statusFilter) params.status = statusFilter;
      if (search.trim()) params.q = search.trim();
      const data = await api.admin.students.list(params);
      setStudents(Array.isArray(data) ? data : []);
    } catch (e: any) {
      flash("err", e.response?.data?.error || "Failed to load students");
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, [scoped, scopedGrade, scopedSection, selectedClass, selectedSection, statusFilter, search]);

  // Section strengths for the active class (drives the balance bar + dropdowns).
  const fetchStrengths = useCallback(async () => {
    const grade = scoped ? scopedGrade : selectedClass;
    if (!grade) {
      setStrengths({});
      return;
    }
    try {
      const data = await api.admin.students.sections(grade);
      setStrengths(data.strengths || {});
      if (data.capacity) setCapacity(data.capacity);
    } catch {
      setStrengths({});
    }
  }, [scoped, scopedGrade, selectedClass]);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);
  useEffect(() => {
    fetchStrengths();
  }, [fetchStrengths]);

  // Lock background scroll while a modal is open.
  useEffect(() => {
    if (showForm || transferStudent) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [showForm, transferStudent]);

  const openAdd = () => {
    setFormData({
      ...emptyForm,
      class_grade: scoped ? scopedGrade! : selectedClass,
      section: scoped ? scopedSection! : "",
      joining_date: new Date().toISOString().slice(0, 10),
    });
    setEditingId(null);
    setShowForm(true);
  };

  const openEdit = (s: Student) => {
    setFormData({
      full_name: s.full_name || `${s.first_name} ${s.last_name}`.trim(),
      admission_number: s.admission_no || "",
      roll_no: s.roll_no != null ? String(s.roll_no) : "",
      class_grade: s.class_grade,
      section: s.section,
      date_of_birth: s.date_of_birth ? s.date_of_birth.slice(0, 10) : "",
      gender: s.gender || "",
      father_name: s.father_name || "",
      mother_name: s.mother_name || "",
      email: s.email || "",
      phone: s.contact_number || "",
      address: s.address || "",
      blood_group: s.blood_group || "",
      joining_date: s.admission_date ? s.admission_date.slice(0, 10) : "",
      status: s.status || "Active",
    });
    setEditingId(s.id);
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({ ...emptyForm });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name.trim()) return flash("err", "Name is required");
    if (!formData.class_grade) return flash("err", "Class is required");
    try {
      const payload: any = {
        full_name: formData.full_name.trim(),
        date_of_birth: formData.date_of_birth || null,
        gender: formData.gender || null,
        father_name: formData.father_name || null,
        mother_name: formData.mother_name || null,
        email: formData.email || null,
        phone: formData.phone || null,
        address: formData.address || null,
        blood_group: formData.blood_group || null,
        class_grade: formData.class_grade,
        joining_date: formData.joining_date || null,
        status: formData.status,
      };
      // Only send section when the user picked one; blank means "auto-balance".
      if (formData.section) payload.section = formData.section;
      // Optional org-supplied numbers; blank => auto (continues org's pattern).
      if (formData.admission_number.trim()) payload.admission_number = formData.admission_number.trim();
      if (formData.roll_no.trim()) payload.roll_no = formData.roll_no.trim();

      if (editingId) {
        await api.admin.students.update(editingId, payload);
        flash("ok", "Student updated");
      } else {
        const created = await api.admin.students.create(payload);
        if (created.auto_section) {
          flash(
            "ok",
            `Added to Section ${created.section} (lowest strength)${
              created.over_capacity ? " — note: all sections at capacity" : ""
            }`
          );
        } else {
          flash("ok", `Student added (roll #${created.roll_no ?? "—"})`);
        }
      }
      resetForm();
      await Promise.all([fetchStudents(), fetchStrengths()]);
    } catch (e: any) {
      flash("err", e.response?.data?.error || "Failed to save student");
    }
  };

  const handleDelete = async (s: Student) => {
    if (!window.confirm(`Delete ${s.full_name} (roll #${s.roll_no ?? "—"})?`)) return;
    try {
      await api.admin.students.delete(s.id);
      flash("ok", "Student deleted");
      await Promise.all([fetchStudents(), fetchStrengths()]);
    } catch (e: any) {
      flash("err", e.response?.data?.error || "Failed to delete");
    }
  };

  const submitTransfer = async () => {
    if (!transferStudent || !transferSection) return;
    try {
      await api.admin.students.transfer(transferStudent.id, { section: transferSection });
      flash("ok", `Moved to Section ${transferSection}`);
      setTransferStudent(null);
      setTransferSection("");
      await Promise.all([fetchStudents(), fetchStrengths()]);
    } catch (e: any) {
      flash("err", e.response?.data?.error || "Transfer failed");
    }
  };

  const handleResequence = async () => {
    const grade = scoped ? scopedGrade! : selectedClass;
    const section = scoped ? scopedSection! : selectedSection;
    if (!grade || !section) return flash("err", "Pick a class and section first");
    if (!window.confirm(`Renumber roll numbers alphabetically for ${grade}-${section}?`)) return;
    try {
      const res = await api.admin.students.resequenceRolls({ class_grade: grade, section });
      flash("ok", res.message || "Rolls renumbered");
      await fetchStudents();
    } catch (e: any) {
      flash("err", e.response?.data?.error || "Failed to renumber");
    }
  };

  const formSections = scoped ? [scopedSection!] : sectionsForClass(formData.class_grade);
  const filterSections = scoped ? [scopedSection!] : sectionsForClass(selectedClass);
  const activeCount = students.filter((s) => (s.status || "").toLowerCase() === "active").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            {scoped ? `My Class — ${scopedGrade} ${scopedSection}` : "Students"}
          </h2>
          <p className="text-sm text-slate-500">
            {scoped
              ? "Manage students of your class. Roll numbers stay alphabetical automatically."
              : "Add, edit, transfer and balance students. Roll & admission numbers are generated automatically."}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleResequence}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-medium px-4 py-2 rounded-lg"
          >
            🔢 Renumber rolls
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="bg-white hover:bg-emerald-50 text-emerald-700 border border-emerald-300 font-medium px-4 py-2 rounded-lg"
          >
            ⬆️ Import CSV/Excel
          </button>
          <button
            onClick={openAdd}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg"
          >
            + Add Student
          </button>
        </div>
      </div>

      {message && (
        <div
          className={`p-3 rounded text-sm font-medium ${
            message.kind === "ok" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Filters (admin/principal) */}
      {!scoped && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Class</label>
            <select
              value={selectedClass}
              onChange={(e) => {
                setSelectedClass(e.target.value);
                setSelectedSection("");
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              <option value="">All classes</option>
              {classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Section</label>
            <select
              value={selectedSection}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              disabled={!selectedClass}
            >
              <option value="">All sections</option>
              {filterSections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            >
              <option value="">Any status</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Search</label>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name / ID / admission no"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>
        </div>
      )}

      {/* Section strength bar */}
      {Object.keys(strengths).length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-slate-600 mb-2">
            Section strengths {scoped ? `(${scopedGrade})` : selectedClass ? `(Class ${selectedClass})` : ""} · capacity {capacity}/section
          </p>
          <div className="flex flex-wrap gap-3">
            {Object.entries(strengths)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([sec, count]) => {
                const pct = Math.min(100, Math.round((count / capacity) * 100));
                const full = count >= capacity;
                return (
                  <div key={sec} className="w-32">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-slate-700">Sec {sec}</span>
                      <span className={full ? "text-red-600 font-semibold" : "text-slate-500"}>
                        {count}/{capacity}
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded">
                      <div
                        className={`h-2 rounded ${full ? "bg-red-500" : pct > 80 ? "bg-amber-500" : "bg-emerald-500"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-4 py-3 border-b bg-slate-50 text-sm text-slate-600">
          {loading ? "Loading…" : `${students.length} student(s) · ${activeCount} active`}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Roll</th>
                <th className="px-3 py-2 text-left font-semibold">Admission</th>
                <th className="px-3 py-2 text-left font-semibold">Name</th>
                {!scoped && <th className="px-3 py-2 text-left font-semibold">Class</th>}
                <th className="px-3 py-2 text-left font-semibold">Gender</th>
                <th className="px-3 py-2 text-left font-semibold">DOB</th>
                <th className="px-3 py-2 text-left font-semibold">Father</th>
                <th className="px-3 py-2 text-left font-semibold">Mother</th>
                <th className="px-3 py-2 text-left font-semibold">Parent Email</th>
                <th className="px-3 py-2 text-left font-semibold">Contact</th>
                <th className="px-3 py-2 text-left font-semibold">Blood</th>
                <th className="px-3 py-2 text-left font-semibold">Address</th>
                <th className="px-3 py-2 text-left font-semibold">Adm. Date</th>
                <th className="px-3 py-2 text-left font-semibold">Status</th>
                <th className="px-3 py-2 text-left font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.length === 0 && !loading ? (
                <tr>
                  <td colSpan={15} className="px-3 py-8 text-center text-slate-400">
                    No students found.
                  </td>
                </tr>
              ) : (
                students.map((s) => (
                  <tr key={s.id} className="border-b hover:bg-slate-50">
                    <td className="px-3 py-2 font-semibold">{s.roll_no ?? "—"}</td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{s.admission_no}</td>
                    <td className="px-3 py-2 font-medium whitespace-nowrap">{s.full_name}</td>
                    {!scoped && (
                      <td className="px-3 py-2 whitespace-nowrap">
                        {s.class_grade}-{s.section}
                      </td>
                    )}
                    <td className="px-3 py-2 text-slate-600">{s.gender || "—"}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">{s.date_of_birth ? s.date_of_birth.slice(0, 10) : "—"}</td>
                    <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{s.father_name || "—"}</td>
                    <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{s.mother_name || "—"}</td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{s.email || "—"}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">{s.contact_number || "—"}</td>
                    <td className="px-3 py-2 text-xs">{s.blood_group || "—"}</td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{s.address || "—"}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap">{s.admission_date ? s.admission_date.slice(0, 10) : "—"}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          (s.status || "").toLowerCase() === "active"
                            ? "bg-green-100 text-green-800"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {s.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => openEdit(s)}
                          className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-2.5 py-1.5 rounded"
                        >
                          Edit
                        </button>
                        {!scoped && (
                          <button
                            onClick={() => {
                              setTransferStudent(s);
                              setTransferSection("");
                            }}
                            className="bg-white hover:bg-indigo-50 text-indigo-700 border border-indigo-300 text-xs font-medium px-2.5 py-1.5 rounded"
                          >
                            Transfer
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(s)}
                          className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-2.5 py-1.5 rounded"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit modal */}
      {showForm && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4 sm:p-6"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) resetForm();
          }}
        >
          <form
            onSubmit={handleSubmit}
            className="bg-white p-6 rounded-lg shadow-2xl space-y-4 w-full max-w-2xl my-8 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-slate-900">
                {editingId ? "Edit student" : "Add student"}
              </h3>
              <button
                type="button"
                onClick={resetForm}
                className="text-slate-400 hover:text-slate-700 text-2xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Full name *</label>
              <input
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full border rounded px-3 py-2"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Father's name</label>
                <input
                  value={formData.father_name}
                  onChange={(e) => setFormData({ ...formData, father_name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Mother's name</label>
                <input
                  value={formData.mother_name}
                  onChange={(e) => setFormData({ ...formData, mother_name: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Phone</label>
                <input
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Class *</label>
                {scoped ? (
                  <input value={scopedGrade} disabled className="w-full border rounded px-3 py-2 bg-slate-100 text-slate-500" />
                ) : (
                  <select
                    value={formData.class_grade}
                    onChange={(e) => setFormData({ ...formData, class_grade: e.target.value, section: "" })}
                    className="w-full border rounded px-3 py-2"
                    required
                  >
                    <option value="">Select class</option>
                    {classes.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Section</label>
                {scoped ? (
                  <input value={scopedSection} disabled className="w-full border rounded px-3 py-2 bg-slate-100 text-slate-500" />
                ) : (
                  <select
                    value={formData.section}
                    onChange={(e) => setFormData({ ...formData, section: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Auto (lowest strength)</option>
                    {formSections.map((s) => (
                      <option key={s} value={s}>
                        Section {s}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Date of birth</label>
                <input
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Gender</label>
                <select
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  {GENDERS.map((g) => (
                    <option key={g} value={g}>{g || "—"}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Blood group</label>
                <select
                  value={formData.blood_group}
                  onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  {BLOOD_GROUPS.map((b) => (
                    <option key={b} value={b}>{b || "—"}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Address</label>
              <input
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full border rounded px-3 py-2"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Admission date</label>
                <input
                  type="date"
                  value={formData.joining_date}
                  onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Optional org-supplied numbers — leave blank to auto-generate */}
            <div className="grid grid-cols-2 gap-3 border-t pt-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Admission no <span className="font-normal text-slate-400">(blank = auto)</span>
                </label>
                <input
                  value={formData.admission_number}
                  onChange={(e) => setFormData({ ...formData, admission_number: e.target.value })}
                  placeholder={editingId ? "" : "auto-generated"}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Roll no <span className="font-normal text-slate-400">(blank = auto)</span>
                </label>
                <input
                  type="number"
                  value={formData.roll_no}
                  onChange={(e) => setFormData({ ...formData, roll_no: e.target.value })}
                  placeholder={editingId ? "" : "auto"}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
            </div>

            {!editingId && (
              <p className="text-xs text-slate-500">
                Leave admission no &amp; roll no blank to auto-generate — admission numbers continue
                your organization's existing pattern. Leaving section on "Auto" places the student in
                the least-full section.
              </p>
            )}

            <div className="flex gap-2 pt-2">
              <button type="submit" className="bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded">
                {editingId ? "Save changes" : "Add student"}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium px-4 py-2 rounded"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Bulk import wizard */}
      {showImport && (
        <ImportWizard
          entity="students"
          onClose={() => setShowImport(false)}
          onImported={() => {
            fetchStudents();
            fetchStrengths();
          }}
        />
      )}

      {/* Transfer modal */}
      {transferStudent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setTransferStudent(null);
          }}
        >
          <div className="bg-white p-6 rounded-lg shadow-2xl w-full max-w-sm space-y-4">
            <h3 className="text-lg font-semibold text-slate-900">Transfer section</h3>
            <p className="text-sm text-slate-600">
              Move <strong>{transferStudent.full_name}</strong> from{" "}
              <strong>
                {transferStudent.class_grade}-{transferStudent.section}
              </strong>{" "}
              to another section of the same class. Both sections are renumbered.
            </p>
            <select
              value={transferSection}
              onChange={(e) => setTransferSection(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="">Select destination section…</option>
              {sectionsForClass(transferStudent.class_grade)
                .filter((s) => s !== transferStudent.section)
                .map((s) => (
                  <option key={s} value={s}>
                    Section {s} ({strengths[s] ?? 0}/{capacity})
                  </option>
                ))}
            </select>
            <div className="flex gap-2">
              <button
                onClick={submitTransfer}
                disabled={!transferSection}
                className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-100 disabled:text-slate-400 font-medium px-4 py-2 rounded"
              >
                Transfer
              </button>
              <button
                onClick={() => setTransferStudent(null)}
                className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium px-4 py-2 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
