import React, { useState, useEffect } from "react";
import { api } from "../api";

interface LeaveRequest {
  id: number;
  teacher_id: number;
  teacher_name: string | null;
  leave_date: string;
  reason: string;
  leave_type: string;
  status: string; // backend stores lowercase: pending | approved | rejected
  substitute_teacher_id?: number;
  substitute_teacher_name?: string | null;
}

interface Substitute {
  id: number;
  name: string;
  subjects?: string[];
  load?: number;
}

interface TeacherLite {
  id: number;
  name: string;
}

type AvailStatus = "free" | "unavailable_marked" | "busy";

interface AvailTeacher {
  id: number;
  name: string;
  status: AvailStatus;
  conflict_periods: number[];
  on_leave: boolean;
}

// 🟢 free · 🟡 free but flagged the slot unavailable · 🔴 already has a class
const statusSymbol = (s: AvailStatus) =>
  s === "free" ? "🟢" : s === "unavailable_marked" ? "🟡" : "🔴";
const statusText = (s: AvailStatus) =>
  s === "free" ? "free" : s === "unavailable_marked" ? "free · marked unavailable" : "has a class";
const availLabel = (t: AvailTeacher) => `${statusSymbol(t.status)} ${t.name} — ${statusText(t.status)}`;

interface LeaveManagementProps {
  // "full": principal — accept/reject + mark absent + substitutes.
  // "substitute": admin — only assign/change substitutes on approved leaves.
  mode?: "full" | "substitute";
}

export default function LeaveManagement({ mode = "full" }: LeaveManagementProps) {
  const canDecide = mode === "full"; // accept/reject + mark-absent gated to principal
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [teachers, setTeachers] = useState<TeacherLite[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [substitutes, setSubstitutes] = useState<Substitute[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [absentTeacher, setAbsentTeacher] = useState<string>("");
  const [absentSub, setAbsentSub] = useState<string>("");
  const [manualSub, setManualSub] = useState<string>("");
  // Availability lists keyed for the two flows.
  const [absentAvail, setAbsentAvail] = useState<AvailTeacher[]>([]);
  const [leaveAvail, setLeaveAvail] = useState<AvailTeacher[]>([]);

  useEffect(() => {
    fetchLeaves();
    api.get("/admin/teachers").then((r) => setTeachers(r.data || [])).catch(() => {});
  }, []);

  // Load substitute availability for the Emergency action whenever the absent
  // teacher changes (status is relative to that teacher's periods today).
  useEffect(() => {
    setAbsentSub("");
    if (!absentTeacher) { setAbsentAvail([]); return; }
    const today = new Date().toISOString().split("T")[0];
    fetchAvailability(Number(absentTeacher), today)
      .then(setAbsentAvail)
      .catch(() => setAbsentAvail([]));
  }, [absentTeacher]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchAvailability = async (absentId: number, date: string): Promise<AvailTeacher[]> => {
    const r = await api.get("/substitute-availability", { params: { absent_teacher_id: absentId, date } });
    return Array.isArray(r.data) ? r.data : [];
  };

  const fetchLeaves = async () => {
    try {
      setLoading(true);
      const response = await api.get("/leaves");
      setLeaves(response.data || []);
    } catch (error) {
      setMessage("❌ Error loading leave requests");
    } finally {
      setLoading(false);
    }
  };

  const errMsg = (error: any, fallback: string) =>
    error?.response?.data?.error || error?.response?.data?.message || error?.message || fallback;

  const isPending = (s: string) => (s || "").toLowerCase() === "pending";

  const approve = async (leaveId: number, substituteId?: number) => {
    try {
      setBusyId(leaveId);
      setMessage("⏳ Approving leave…");
      await api.post(`/leaves/${leaveId}/approve`, {
        substitute_teacher_id: substituteId ?? null,
        auto_adjust: true,
      });
      setMessage("✅ Leave approved" + (substituteId ? " with the selected substitute." : " (a substitute was auto-assigned if available)."));
      setExpanded(null);
      setSubstitutes([]);
      setManualSub("");
      fetchLeaves();
    } catch (error: any) {
      setMessage(`❌ ${errMsg(error, "Could not approve the leave")}`);
    } finally {
      setBusyId(null);
    }
  };

  // Assign/change the substitute on an already-approved leave (admin flow).
  const setSubstitute = async (leaveId: number, substituteId?: number) => {
    try {
      setBusyId(leaveId);
      setMessage("⏳ Updating substitute…");
      await api.post(`/leaves/${leaveId}/substitute`, {
        substitute_teacher_id: substituteId ?? null,
      });
      setMessage(substituteId ? "✅ Substitute updated." : "✅ Substitute auto-assigned.");
      setExpanded(null);
      setSubstitutes([]);
      setManualSub("");
      fetchLeaves();
    } catch (error: any) {
      setMessage(`❌ ${errMsg(error, "Could not update the substitute")}`);
    } finally {
      setBusyId(null);
    }
  };

  // Route an "assign substitute" action to the right backend call depending on
  // whether the leave is still pending (approve) or already approved (set sub).
  const assignSubstitute = (leave: LeaveRequest, substituteId?: number) =>
    isPending(leave.status) ? approve(leave.id, substituteId) : setSubstitute(leave.id, substituteId);

  const reject = async (leaveId: number) => {
    const reason = window.prompt("Reason for rejecting this leave request?", "Not approved");
    if (reason === null) return;
    try {
      setBusyId(leaveId);
      setMessage("⏳ Rejecting leave…");
      await api.post(`/leaves/${leaveId}/reject`, { rejection_reason: reason || "Not approved" });
      setMessage("✅ Leave rejected.");
      setExpanded(null);
      fetchLeaves();
    } catch (error: any) {
      setMessage(`❌ ${errMsg(error, "Could not reject the leave")}`);
    } finally {
      setBusyId(null);
    }
  };

  const findSubstitutes = async (leaveId: number) => {
    if (expanded === leaveId) { setExpanded(null); return; }
    const leave = leaves.find((l) => l.id === leaveId);
    try {
      setExpanded(leaveId);
      setManualSub("");
      setLeaveAvail([]);
      setLoadingSubs(true);
      setSubstitutes([]);
      if (leave) {
        fetchAvailability(leave.teacher_id, leave.leave_date)
          .then(setLeaveAvail)
          .catch(() => setLeaveAvail([]));
      }
      const response = await api.get(`/leaves/${leaveId}/substitute-options`);
      // Endpoint returns a plain array of substitutes.
      setSubstitutes(Array.isArray(response.data) ? response.data : (response.data?.available_substitutes || []));
    } catch (error: any) {
      setMessage(`❌ ${errMsg(error, "Could not load substitutes")}`);
    } finally {
      setLoadingSubs(false);
    }
  };

  const markAbsent = async () => {
    if (!absentTeacher) { setMessage("❌ Pick a teacher to mark absent."); return; }
    try {
      setMessage("⏳ Marking teacher absent…");
      await api.post(`/teachers/${absentTeacher}/mark-absent`, {
        date: new Date().toISOString().split("T")[0],
        reason: "Unannounced absence",
        substitute_teacher_id: absentSub ? Number(absentSub) : null,
      });
      setMessage(absentSub
        ? "✅ Teacher marked absent with the selected substitute."
        : "✅ Teacher marked absent. A substitute was auto-assigned where possible.");
      setAbsentTeacher("");
      setAbsentSub("");
      fetchLeaves();
    } catch (error: any) {
      setMessage(`❌ ${errMsg(error, "Could not mark the teacher absent")}`);
    }
  };

  const statusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s === "approved") return "bg-green-100 text-green-800";
    if (s === "rejected") return "bg-red-100 text-red-800";
    return "bg-yellow-100 text-yellow-800";
  };

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-4 rounded-lg border ${
          message.includes("✅") ? "bg-green-50 border-green-200 text-green-800"
          : message.includes("❌") ? "bg-red-50 border-red-200 text-red-800"
          : "bg-blue-50 border-blue-200 text-blue-800"
        }`}>
          {message}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">📋 Leave Requests</h2>
          <button onClick={fetchLeaves} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium">
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <p className="text-gray-600">Loading leave requests…</p>
        ) : leaves.length === 0 ? (
          <p className="text-gray-600">No leave requests yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold">Teacher</th>
                  <th className="px-4 py-2 text-left font-semibold">Date</th>
                  <th className="px-4 py-2 text-left font-semibold">Reason</th>
                  <th className="px-4 py-2 text-left font-semibold">Type</th>
                  <th className="px-4 py-2 text-left font-semibold">Status</th>
                  <th className="px-4 py-2 text-left font-semibold">Substitute</th>
                  <th className="px-4 py-2 text-left font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leaves.map((leave) => (
                  <React.Fragment key={leave.id}>
                    <tr className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{leave.teacher_name || `Teacher #${leave.teacher_id}`}</td>
                      <td className="px-4 py-2">{leave.leave_date}</td>
                      <td className="px-4 py-2">{leave.reason || "—"}</td>
                      <td className="px-4 py-2 capitalize">{leave.leave_type}</td>
                      <td className="px-4 py-2">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${statusBadge(leave.status)}`}>
                          {leave.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{leave.substitute_teacher_name || "—"}</td>
                      <td className="px-4 py-2">
                        {isPending(leave.status) ? (
                          canDecide ? (
                            <div className="flex flex-wrap gap-2">
                              <button
                                disabled={busyId === leave.id}
                                onClick={() => approve(leave.id)}
                                className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-3 py-1 rounded text-xs font-medium"
                              >
                                ✓ Accept
                              </button>
                              <button
                                disabled={busyId === leave.id}
                                onClick={() => reject(leave.id)}
                                className="bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white px-3 py-1 rounded text-xs font-medium"
                              >
                                ✕ Reject
                              </button>
                              <button
                                onClick={() => findSubstitutes(leave.id)}
                                className="bg-slate-200 hover:bg-slate-300 text-slate-800 px-3 py-1 rounded text-xs font-medium"
                              >
                                {expanded === leave.id ? "Hide" : "Choose substitute"}
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs text-amber-600">Awaiting principal</span>
                          )
                        ) : leave.status.toLowerCase() === "approved" ? (
                          <button
                            onClick={() => findSubstitutes(leave.id)}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded text-xs font-medium"
                          >
                            {expanded === leave.id ? "Hide" : (leave.substitute_teacher_name ? "Change substitute" : "Assign substitute")}
                          </button>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                    {expanded === leave.id && (
                      <tr className="bg-blue-50/50">
                        <td colSpan={7} className="px-4 py-3 space-y-4">
                          {/* Auto-assign shortcut */}
                          <button
                            disabled={busyId === leave.id}
                            onClick={() => assignSubstitute(leave)}
                            className="bg-cyan-600 hover:bg-cyan-700 disabled:opacity-60 text-white px-3 py-1.5 rounded text-xs font-medium"
                          >
                            ⚙️ {isPending(leave.status) ? "Accept & auto-assign substitute" : "Auto-assign best substitute"}
                          </button>

                          {/* Recommended (free + same subject) substitutes */}
                          <div className="space-y-2">
                            <p className="font-semibold text-blue-900 text-sm">⭐ Recommended substitutes (free that day, same subject):</p>
                            {loadingSubs ? (
                              <p className="text-blue-700 text-sm">⏳ Loading available substitutes…</p>
                            ) : substitutes.length === 0 ? (
                              <p className="text-slate-600 text-sm">No free same-subject substitutes found — use manual selection below.</p>
                            ) : (
                              substitutes.map((sub) => (
                                <div key={sub.id} className="flex justify-between items-center bg-white p-2 rounded border border-blue-200">
                                  <div>
                                    <p className="font-medium text-gray-900 text-sm">{sub.name}</p>
                                    {sub.subjects && sub.subjects.length > 0 && (
                                      <p className="text-xs text-gray-500">{sub.subjects.join(", ")}</p>
                                    )}
                                  </div>
                                  <button
                                    disabled={busyId === leave.id}
                                    onClick={() => assignSubstitute(leave, sub.id)}
                                    className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-3 py-1 rounded text-xs font-medium"
                                  >
                                    {isPending(leave.status) ? "Approve with" : "Assign"} {sub.name.split(" ")[0]}
                                  </button>
                                </div>
                              ))
                            )}
                          </div>

                          {/* Manual selection — any teacher */}
                          <div className="bg-white p-3 rounded border border-slate-200 space-y-2">
                            <p className="font-semibold text-slate-800 text-sm">✍️ Or manually assign any teacher:</p>
                            <div className="flex flex-wrap gap-2 items-center">
                              <select
                                value={manualSub}
                                onChange={(e) => setManualSub(e.target.value)}
                                className="border rounded px-3 py-2 text-sm min-w-72"
                              >
                                <option value="">Select a teacher…</option>
                                {(leaveAvail.length
                                  ? leaveAvail
                                  : teachers
                                      .filter((t) => t.id !== leave.teacher_id)
                                      .map((t) => ({ id: t.id, name: t.name, status: "free" as AvailStatus, conflict_periods: [], on_leave: false }))
                                ).map((t) => (
                                  <option key={t.id} value={t.id}>{availLabel(t)}</option>
                                ))}
                              </select>
                              <button
                                disabled={busyId === leave.id || !manualSub}
                                onClick={() => assignSubstitute(leave, Number(manualSub))}
                                className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-2 rounded text-sm font-medium"
                              >
                                {isPending(leave.status) ? "Approve with selected" : "Assign selected"}
                              </button>
                            </div>
                            <p className="text-xs text-slate-500">
                              🟢 free · 🟡 free but flagged the slot unavailable · 🔴 already has a class.
                              The teacher must be free during the absent teacher's periods that day, otherwise it is rejected.
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Emergency Actions — principal only (admins cannot mark present/absent) */}
      {canDecide && (
      <div className="bg-gradient-to-r from-red-50 to-red-100 rounded-lg p-6 border-2 border-red-200">
        <h3 className="text-xl font-bold text-red-900 mb-2">🚨 Emergency Actions</h3>
        <p className="text-red-700 mb-4">Mark a teacher as absent today, then auto-assign a substitute or pick one yourself.</p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-red-900 mb-1">Absent teacher</label>
            <select
              value={absentTeacher}
              onChange={(e) => setAbsentTeacher(e.target.value)}
              className="border rounded px-3 py-2 min-w-56"
            >
              <option value="">Select a teacher…</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-red-900 mb-1">Substitute</label>
            <select
              value={absentSub}
              onChange={(e) => setAbsentSub(e.target.value)}
              className="border rounded px-3 py-2 min-w-72"
            >
              <option value="">⚙️ Auto-assign (recommended)</option>
              {(absentAvail.length
                ? absentAvail
                : teachers
                    .filter((t) => String(t.id) !== absentTeacher)
                    .map((t) => ({ id: t.id, name: t.name, status: "free" as AvailStatus, conflict_periods: [], on_leave: false }))
              ).map((t) => (
                <option key={t.id} value={t.id}>{availLabel(t)}</option>
              ))}
            </select>
          </div>
          <button
            onClick={markAbsent}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium"
          >
            Mark Teacher Absent Today
          </button>
        </div>
        <p className="text-xs text-red-700 mt-3">
          Substitute status: 🟢 free · 🟡 free but flagged the slot unavailable · 🔴 already has a class.
        </p>
      </div>
      )}

      {!canDecide && (
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 text-sm text-blue-800">
          ℹ️ As an admin you can assign or change substitute teachers for approved/absent leaves.
          Accepting/rejecting leave and marking teachers absent is handled by the principal.
        </div>
      )}
    </div>
  );
}
