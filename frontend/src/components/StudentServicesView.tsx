import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Loan {
  id: number;
  book_title: string | null;
  issued_on: string | null;
  due_on: string | null;
  status: string;
  overdue: boolean;
}

interface Transport {
  id: number;
  route_name: string | null;
  stop_name: string | null;
  driver_name: string | null;
  driver_phone: string | null;
  vehicle_no: string | null;
}

export default function StudentServicesView({ studentId }: { studentId?: number }) {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [transport, setTransport] = useState<Transport[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const [lib, trn] = await Promise.all([
          (studentId ? api.library.student(studentId) : api.library.my()).catch(() => ({ loans: [] })),
          (studentId ? api.transport.student(studentId) : api.transport.my()).catch(() => ({ transport: [] })),
        ]);
        if (active) {
          setLoans(lib.loans || []);
          setTransport(trn.transport || []);
        }
      } catch (e: any) {
        if (active) setErr(e?.response?.data?.error || "Could not load services.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [studentId]);

  if (loading) return <div className="text-sm text-slate-500">Loading…</div>;
  if (err) return <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 font-semibold text-slate-800">🚌 Transport</h3>
        {transport.length ? transport.map((t) => (
          <div key={t.id} className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <div className="font-medium text-slate-800">{t.route_name}{t.vehicle_no ? ` · ${t.vehicle_no}` : ""}</div>
            <div className="mt-1 text-slate-600">
              {t.stop_name ? `Stop: ${t.stop_name}` : "No stop set"}
              {t.driver_name ? ` · Driver: ${t.driver_name}` : ""}
              {t.driver_phone ? ` (${t.driver_phone})` : ""}
            </div>
          </div>
        )) : <div className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-sm text-slate-400">Not assigned to any route.</div>}
      </div>

      <div>
        <h3 className="mb-2 font-semibold text-slate-800">📚 Library</h3>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-2">Book</th><th className="px-4 py-2">Issued</th><th className="px-4 py-2">Due</th><th className="px-4 py-2">Status</th></tr></thead>
            <tbody>
              {loans.map((l) => (
                <tr key={l.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-medium text-slate-800">{l.book_title}</td>
                  <td className="px-4 py-2">{l.issued_on || "—"}</td>
                  <td className="px-4 py-2">{l.due_on || "—"}</td>
                  <td className="px-4 py-2">
                    {l.status === "returned" ? <span className="text-slate-500">returned</span>
                      : l.overdue ? <span className="font-semibold text-rose-600">overdue</span>
                      : <span className="text-blue-700">issued</span>}
                  </td>
                </tr>
              ))}
              {!loans.length && <tr><td colSpan={4} className="px-4 py-6 text-center text-slate-400">No library activity.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
