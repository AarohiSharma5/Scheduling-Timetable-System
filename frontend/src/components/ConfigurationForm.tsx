import React, { useState, useEffect } from "react";
import { api } from "../api";

interface SchoolConfig {
  id: number;
  start_time: string;
  end_time: string;
  lunch_start: string;
  lunch_end: string;
  period_duration: number;
  periods_per_day: number;
  working_days: number;
}

export default function ConfigurationForm() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [config, setConfig] = useState<SchoolConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState({
    start_time: "08:00",
    end_time: "15:00",
    lunch_start: "12:00",
    lunch_end: "13:00",
    period_duration: 45,
    periods_per_day: 6,
    working_days: 5,
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const res = await api.admin.config.get();
      if (res.data) {
        setConfig(res.data);
        setFormData(res.data);
      }
    } catch (err) {
      setError("Failed to load configuration");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError("");
      setSuccess("");
      await api.admin.config.update(formData);
      setSuccess("Configuration saved successfully!");
      await loadConfig();
    } catch (err) {
      setError("Failed to save configuration");
      console.error(err);
    }
  };

  if (loading) return <div className="text-center py-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900">School Configuration</h2>

      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">{success}</div>}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-6">
        {/* School Hours */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">School Hours</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Start Time</label>
              <input
                type="time"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">End Time</label>
              <input
                type="time"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
          </div>
        </div>

        {/* Lunch Break */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Lunch Break</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Lunch Start</label>
              <input
                type="time"
                value={formData.lunch_start}
                onChange={(e) => setFormData({ ...formData, lunch_start: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Lunch End</label>
              <input
                type="time"
                value={formData.lunch_end}
                onChange={(e) => setFormData({ ...formData, lunch_end: e.target.value })}
                className="border rounded px-3 py-2 w-full"
                required
              />
            </div>
          </div>
        </div>

        {/* Period Configuration */}
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Period Configuration</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Period Duration (minutes)</label>
              <input
                type="number"
                value={formData.period_duration}
                onChange={(e) => setFormData({ ...formData, period_duration: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="30"
                max="60"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Periods Per Day</label>
              <input
                type="number"
                value={formData.periods_per_day}
                onChange={(e) => setFormData({ ...formData, periods_per_day: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="4"
                max="12"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Working Days</label>
              <input
                type="number"
                value={formData.working_days}
                onChange={(e) => setFormData({ ...formData, working_days: Number(e.target.value) })}
                className="border rounded px-3 py-2 w-full"
                min="3"
                max="6"
                required
              />
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-slate-900 mb-2">Summary</h4>
          <ul className="text-sm text-slate-700 space-y-1">
            <li>
              📅 <strong>Daily Schedule:</strong> {formData.start_time} - {formData.end_time} ({formData.periods_per_day} periods × {formData.period_duration} min)
            </li>
            <li>
              🍽️ <strong>Lunch Break:</strong> {formData.lunch_start} - {formData.lunch_end}
            </li>
            <li>
              📆 <strong>Working Days:</strong> {formData.working_days} days/week
            </li>
          </ul>
        </div>

        <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-3 rounded-lg">
          Save Configuration
        </button>
      </form>
    </div>
  );
}
