import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Route {
  id: number;
  name: string;
  description: string | null;
  driver_name: string | null;
  driver_phone: string | null;
  vehicle_no: string | null;
  capacity: number | null;
  assigned_count: number | null;
}

interface Assignment {
  id: number;
  student_id: number;
  student_name: string | null;
  stop_name: string | null;
}

interface StudentResult {
  id: number;
  full_name: string;
  class_grade: string;
  section: string;
}

export default function TransportPanel() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [name, setName] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [driver, setDriver] = useState("");
  const [phone, setPhone] = useState("");
  const [capacity, setCapacity] = useState("");

  const [openRoute, setOpenRoute] = useState<number | null>(null);
  const [assigns, setAssigns] = useState<Assignment[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StudentResult[]>([]);
  const [stop, setStop] = useState("");

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 2500); };

  const load = async () => setRoutes(await api.transport.routes());
  useEffect(() => { load().catch(() => setErr("Could not load routes.")); }, []);

  const createRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.transport.createRoute({
        name: name.trim(), vehicle_no: vehicle.trim() || undefined,
        driver_name: driver.trim() || undefined, driver_phone: phone.trim() || undefined,
        capacity: capacity ? Number(capacity) : undefined,
      });
      setName(""); setVehicle(""); setDriver(""); setPhone(""); setCapacity("");
      flash("Route added.");
      load();
    } catch (e: any) { setErr(e?.response?.data?.error || "Could not create route."); }
  };

  const removeRoute = async (id: number) => {
    if (!window.confirm("Delete this route and its assignments?")) return;
    await api.transport.removeRoute(id);
    if (openRoute === id) setOpenRoute(null);
    load();
  };

  const openStudents = async (id: number) => {
    if (openRoute === id) { setOpenRoute(null); return; }
    setAssigns(await api.transport.routeStudents(id));
    setOpenRoute(id); setQuery(""); setResults([]); setStop("");
  };

  const search = async () => {
    if (!query.trim()) return;
    setResults(await api.admin.students.list({ q: query.trim() }));
  };

  const assign = async (studentId: number) => {
    if (openRoute == null) return;
    try {
      await api.transport.assign(openRoute, { student_id: studentId, stop_name: stop.trim() || undefined });
      setAssigns(await api.transport.routeStudents(openRoute));
      setResults([]); setQuery("");
      flash("Student assigned.");
      load();
    } catch (e: any) { setErr(e?.response?.data?.error || "Could not assign."); }
  };

  const unassign = async (assignmentId: number) => {
    if (openRoute == null) return;
    await api.transport.unassign(assignmentId);
    setAssigns(await api.transport.routeStudents(openRoute));
    load();
  };

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-slate-800">Transport</h2>
      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}

      <form onSubmit={createRoute} className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-5">
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Route name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Vehicle no" value={vehicle} onChange={(e) => setVehicle(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Driver" value={driver} onChange={(e) => setDriver(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Driver phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="number" placeholder="Capacity" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-5">Add route</button>
      </form>

      <div className="space-y-3">
        {routes.map((r) => (
          <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold text-slate-800">{r.name} {r.vehicle_no && <span className="text-xs text-slate-400">· {r.vehicle_no}</span>}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {r.driver_name ? `Driver: ${r.driver_name}` : "No driver"}{r.driver_phone ? ` (${r.driver_phone})` : ""}
                  {" · "}{r.assigned_count ?? 0}{r.capacity ? `/${r.capacity}` : ""} students
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button onClick={() => openStudents(r.id)} className="rounded-md bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{openRoute === r.id ? "Hide" : "Students"}</button>
                <button onClick={() => removeRoute(r.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
              </div>
            </div>

            {openRoute === r.id && (
              <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
                <div className="flex flex-wrap gap-2">
                  <input className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Search student" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} />
                  <input className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Stop name" value={stop} onChange={(e) => setStop(e.target.value)} />
                  <button onClick={search} className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white">Search</button>
                </div>
                {results.length > 0 && (
                  <div className="space-y-1">
                    {results.map((s) => (
                      <button key={s.id} onClick={() => assign(s.id)} className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-emerald-50">
                        <span>{s.full_name} <span className="text-xs text-slate-400">({s.class_grade}-{s.section})</span></span>
                        <span className="text-xs font-semibold text-emerald-600">Assign →</span>
                      </button>
                    ))}
                  </div>
                )}
                <div className="overflow-hidden rounded-lg border border-slate-200">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 text-slate-500"><tr><th className="px-3 py-2">Student</th><th className="px-3 py-2">Stop</th><th className="px-3 py-2 text-right">Action</th></tr></thead>
                    <tbody>
                      {assigns.map((a) => (
                        <tr key={a.id} className="border-t border-slate-100">
                          <td className="px-3 py-2 font-medium text-slate-800">{a.student_name}</td>
                          <td className="px-3 py-2">{a.stop_name || "—"}</td>
                          <td className="px-3 py-2 text-right"><button onClick={() => unassign(a.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Remove</button></td>
                        </tr>
                      ))}
                      {!assigns.length && <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-400">No students assigned.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
        {!routes.length && <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">No routes yet.</div>}
      </div>
    </div>
  );
}
