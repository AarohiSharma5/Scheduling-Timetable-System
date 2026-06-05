import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Payment {
  id: number;
  amount: number;
  method: string;
  paid_on: string | null;
}

interface Invoice {
  id: number;
  title: string;
  amount: number;
  amount_paid: number;
  balance: number;
  status: string;
  due_date: string | null;
  payments: Payment[];
}

interface Data {
  student?: { id: number; name?: string; class?: string };
  totals: { billed: number; paid: number; outstanding: number };
  invoices: Invoice[];
}

const money = (n: number) =>
  "\u20b9" + (n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

const statusBadge = (s: string) => {
  const map: Record<string, string> = {
    pending: "bg-rose-100 text-rose-700",
    partial: "bg-amber-100 text-amber-800",
    paid: "bg-emerald-100 text-emerald-800",
    waived: "bg-slate-100 text-slate-600",
  };
  return map[s] || "bg-slate-100 text-slate-700";
};

export default function StudentFeesView({ studentId }: { studentId?: number }) {
  const [data, setData] = useState<Data | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const res = studentId ? await api.fees.student(studentId) : await api.fees.my();
        if (active) setData(res);
      } catch (e: any) {
        if (active) setErr(e?.response?.data?.error || "Could not load fees.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [studentId]);

  if (loading) return <div className="text-sm text-slate-500">Loading fees…</div>;
  if (err) return <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs text-slate-500">Billed</div>
          <div className="mt-1 text-lg font-bold text-slate-800">{money(data.totals.billed)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs text-slate-500">Paid</div>
          <div className="mt-1 text-lg font-bold text-emerald-600">{money(data.totals.paid)}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs text-slate-500">Outstanding</div>
          <div className="mt-1 text-lg font-bold text-rose-600">{money(data.totals.outstanding)}</div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2">Fee</th><th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Paid</th><th className="px-4 py-2">Balance</th>
              <th className="px-4 py-2">Due</th><th className="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.invoices.map((inv) => (
              <tr key={inv.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium text-slate-800">{inv.title}</td>
                <td className="px-4 py-2">{money(inv.amount)}</td>
                <td className="px-4 py-2">{money(inv.amount_paid)}</td>
                <td className="px-4 py-2">{money(inv.balance)}</td>
                <td className="px-4 py-2">{inv.due_date || "—"}</td>
                <td className="px-4 py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(inv.status)}`}>{inv.status}</span></td>
              </tr>
            ))}
            {!data.invoices.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-slate-400">No fees on record.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
