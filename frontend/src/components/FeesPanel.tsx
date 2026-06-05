import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Structure {
  id: number;
  name: string;
  amount: number;
  grade: string | null;
  term: string | null;
  due_date: string | null;
}

interface Invoice {
  id: number;
  student_id: number;
  student_name: string | null;
  title: string;
  amount: number;
  amount_paid: number;
  balance: number;
  status: string;
  due_date: string | null;
}

interface Summary {
  billed: number;
  collected: number;
  outstanding: number;
  invoice_count: number;
  by_status: Record<string, number>;
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

export default function FeesPanel() {
  const [tab, setTab] = useState<"overview" | "structures" | "invoices">("overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [structures, setStructures] = useState<Structure[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  // structure form
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [grade, setGrade] = useState("");
  const [term, setTerm] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);

  // payment entry
  const [payFor, setPayFor] = useState<number | null>(null);
  const [payAmount, setPayAmount] = useState("");
  const [payMethod, setPayMethod] = useState("cash");

  const flash = (m: string) => {
    setMsg(m);
    setTimeout(() => setMsg(""), 2500);
  };

  const loadAll = async () => {
    try {
      setLoading(true);
      setErr("");
      const [sum, st, inv] = await Promise.all([
        api.fees.summary(),
        api.fees.structures(),
        api.fees.invoices(statusFilter ? { status: statusFilter } : {}),
      ]);
      setSummary(sum);
      setStructures(st);
      setInvoices(inv);
    } catch {
      setErr("Could not load fee data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const createStructure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !amount) return;
    try {
      setSaving(true);
      await api.fees.createStructure({
        name: name.trim(),
        amount: Number(amount),
        grade: grade.trim() || null,
        term: term.trim() || undefined,
        due_date: dueDate || undefined,
      });
      setName(""); setAmount(""); setGrade(""); setTerm(""); setDueDate("");
      flash("Fee created.");
      loadAll();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Could not create fee.");
    } finally {
      setSaving(false);
    }
  };

  const generate = async (id: number) => {
    try {
      const r = await api.fees.generate(id);
      flash(`Issued ${r.created} invoice(s) (${r.skipped} already existed).`);
      loadAll();
    } catch {
      setErr("Could not issue invoices.");
    }
  };

  const removeStructure = async (id: number) => {
    if (!window.confirm("Delete this fee and all its invoices/payments?")) return;
    await api.fees.removeStructure(id);
    flash("Fee deleted.");
    loadAll();
  };

  const recordPayment = async (inv: Invoice) => {
    if (!payAmount) return;
    try {
      await api.fees.pay(inv.id, { amount: Number(payAmount), method: payMethod });
      setPayFor(null); setPayAmount("");
      flash("Payment recorded.");
      loadAll();
    } catch (e: any) {
      setErr(e?.response?.data?.error || "Could not record payment.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Fees & Payments</h2>
        <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
          {(["overview", "structures", "invoices"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1 text-sm font-medium capitalize ${
                tab === t ? "bg-white text-slate-900 shadow" : "text-slate-500"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}
      {loading && <div className="text-sm text-slate-500">Loading…</div>}

      {tab === "overview" && summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="text-sm text-slate-500">Total billed</div>
            <div className="mt-1 text-2xl font-bold text-slate-800">{money(summary.billed)}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="text-sm text-slate-500">Collected</div>
            <div className="mt-1 text-2xl font-bold text-emerald-600">{money(summary.collected)}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="text-sm text-slate-500">Outstanding</div>
            <div className="mt-1 text-2xl font-bold text-rose-600">{money(summary.outstanding)}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5 sm:col-span-3">
            <div className="text-sm font-medium text-slate-600">
              {summary.invoice_count} invoice(s):
              {" "}{summary.by_status.paid || 0} paid · {summary.by_status.partial || 0} partial ·{" "}
              {summary.by_status.pending || 0} pending
            </div>
          </div>
        </div>
      )}

      {tab === "structures" && (
        <div className="space-y-5">
          <form onSubmit={createStructure} className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-5">
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Fee name (e.g. Term 1)" value={name} onChange={(e) => setName(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Grade (blank = all)" value={grade} onChange={(e) => setGrade(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Term (optional)" value={term} onChange={(e) => setTerm(e.target.value)} />
            <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            <button disabled={saving} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 lg:col-span-5">
              {saving ? "Saving…" : "Add fee"}
            </button>
          </form>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-2">Fee</th><th className="px-4 py-2">Amount</th>
                  <th className="px-4 py-2">Grade</th><th className="px-4 py-2">Due</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {structures.map((s) => (
                  <tr key={s.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-medium text-slate-800">{s.name}{s.term ? ` · ${s.term}` : ""}</td>
                    <td className="px-4 py-2">{money(s.amount)}</td>
                    <td className="px-4 py-2">{s.grade || "All"}</td>
                    <td className="px-4 py-2">{s.due_date || "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => generate(s.id)} className="mr-2 rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">Issue invoices</button>
                      <button onClick={() => removeStructure(s.id)} className="rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
                    </td>
                  </tr>
                ))}
                {!structures.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">No fees defined yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "invoices" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Filter:</span>
            <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="partial">Partial</option>
              <option value="paid">Paid</option>
            </select>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-2">Student</th><th className="px-4 py-2">Fee</th>
                  <th className="px-4 py-2">Amount</th><th className="px-4 py-2">Paid</th>
                  <th className="px-4 py-2">Balance</th><th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <React.Fragment key={inv.id}>
                    <tr className="border-t border-slate-100">
                      <td className="px-4 py-2 font-medium text-slate-800">{inv.student_name || `#${inv.student_id}`}</td>
                      <td className="px-4 py-2">{inv.title}</td>
                      <td className="px-4 py-2">{money(inv.amount)}</td>
                      <td className="px-4 py-2">{money(inv.amount_paid)}</td>
                      <td className="px-4 py-2">{money(inv.balance)}</td>
                      <td className="px-4 py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusBadge(inv.status)}`}>{inv.status}</span></td>
                      <td className="px-4 py-2 text-right">
                        {inv.status !== "paid" && inv.status !== "waived" && (
                          <button onClick={() => { setPayFor(payFor === inv.id ? null : inv.id); setPayAmount(String(inv.balance)); }} className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                            {payFor === inv.id ? "Cancel" : "Record payment"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {payFor === inv.id && (
                      <tr className="bg-indigo-50/50"><td colSpan={7} className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <input className="w-32 rounded-lg border border-slate-300 px-3 py-1.5 text-sm" type="number" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} placeholder="Amount" />
                          <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm" value={payMethod} onChange={(e) => setPayMethod(e.target.value)}>
                            <option value="cash">Cash</option><option value="online">Online</option>
                            <option value="cheque">Cheque</option><option value="other">Other</option>
                          </select>
                          <button onClick={() => recordPayment(inv)} className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white">Save</button>
                        </div>
                      </td></tr>
                    )}
                  </React.Fragment>
                ))}
                {!invoices.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-400">No invoices. Issue some from the Structures tab.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
