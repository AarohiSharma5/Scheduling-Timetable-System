import React, { useEffect, useState } from "react";
import { api } from "../api";

interface Item {
  id: number;
  name: string;
  category: string | null;
  quantity: number;
  unit: string;
  min_quantity: number;
  location: string | null;
  low_stock: boolean;
}

export default function InventoryPanel() {
  const [items, setItems] = useState<Item[]>([]);
  const [lowOnly, setLowOnly] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("unit");
  const [minQty, setMinQty] = useState("");
  const [location, setLocation] = useState("");

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 2500); };

  const load = async () => setItems(await api.inventory.list(lowOnly ? { low: "1" } : {}));
  useEffect(() => { load().catch(() => setErr("Could not load inventory.")); /* eslint-disable-next-line */ }, [lowOnly]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.inventory.create({
        name: name.trim(), category: category.trim() || undefined,
        quantity: Number(quantity) || 0, unit: unit.trim() || "unit",
        min_quantity: Number(minQty) || 0, location: location.trim() || undefined,
      });
      setName(""); setCategory(""); setQuantity(""); setUnit("unit"); setMinQty(""); setLocation("");
      flash("Item added.");
      load();
    } catch (e: any) { setErr(e?.response?.data?.error || "Could not add item."); }
  };

  const adjust = async (item: Item, delta: number) => {
    try { await api.inventory.adjust(item.id, delta); load(); }
    catch (e: any) { setErr(e?.response?.data?.error || "Adjustment failed."); }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this item?")) return;
    await api.inventory.remove(id);
    load();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Inventory</h2>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} /> Low stock only
        </label>
      </div>

      {err && <div className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{err}</div>}
      {msg && <div className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}

      <form onSubmit={create} className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-5 sm:grid-cols-6">
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" placeholder="Item name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="number" placeholder="Qty" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" type="number" placeholder="Reorder at" value={minQty} onChange={(e) => setMinQty(e.target.value)} />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-5" placeholder="Location (optional)" value={location} onChange={(e) => setLocation(e.target.value)} />
        <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">Add</button>
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-2">Item</th><th className="px-4 py-2">Category</th><th className="px-4 py-2">Location</th><th className="px-4 py-2">Quantity</th><th className="px-4 py-2 text-right">Actions</th></tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id} className={`border-t border-slate-100 ${i.low_stock ? "bg-rose-50/40" : ""}`}>
                <td className="px-4 py-2 font-medium text-slate-800">{i.name}{i.low_stock && <span className="ml-2 rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">low</span>}</td>
                <td className="px-4 py-2">{i.category || "—"}</td>
                <td className="px-4 py-2">{i.location || "—"}</td>
                <td className="px-4 py-2">{i.quantity} {i.unit}</td>
                <td className="px-4 py-2 text-right">
                  <div className="inline-flex items-center gap-1">
                    <button onClick={() => adjust(i, -1)} className="h-7 w-7 rounded-md bg-slate-100 font-bold text-slate-700">−</button>
                    <button onClick={() => adjust(i, 1)} className="h-7 w-7 rounded-md bg-slate-100 font-bold text-slate-700">+</button>
                    <button onClick={() => remove(i.id)} className="ml-2 rounded-md bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-slate-400">No items{lowOnly ? " low on stock" : ""}.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
