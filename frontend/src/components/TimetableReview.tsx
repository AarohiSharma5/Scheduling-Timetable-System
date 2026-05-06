import React from "react";
import type { TimetableSlot } from "../types";

export const TimetableReviewComponent: React.FC<{
  timetable: (TimetableSlot | null)[][];
  warnings: string[];
  onExport: () => void;
}> = ({ timetable, warnings, onExport }) => {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Timetable</h3>
        <button onClick={onExport}>Export to CSV</button>
      </div>

      {warnings.length > 0 && (
        <div className="mb-4 rounded bg-yellow-100 p-4">
          <p className="font-semibold text-yellow-800">Warnings:</p>
          <ul className="mt-2 list-inside list-disc text-sm text-yellow-700">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-2 text-left">Day</th>
              {timetable[0]?.map((_, i) => (
                <th key={i} className="border border-gray-300 px-4 py-2">
                  Period {i + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {timetable.map((day, dayIdx) => (
              <tr key={dayIdx}>
                <td className="border border-gray-300 px-4 py-2 font-semibold">
                  {days[dayIdx]}
                </td>
                {day.map((slot, periodIdx) => (
                  <td
                    key={periodIdx}
                    className="border border-gray-300 px-4 py-2 text-sm"
                  >
                    {slot ? (
                      <div>
                        <p className="font-semibold">{slot.subject}</p>
                        <p className="text-gray-600">{slot.teacher}</p>
                      </div>
                    ) : (
                      <span className="text-gray-400">Free</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
