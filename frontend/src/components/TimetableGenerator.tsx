import React, { useState } from "react";
import { api } from "../api";

interface GenerationStatus {
  status: "idle" | "loading" | "success" | "error";
  message: string;
}

export default function TimetableGenerator() {
  const [status, setStatus] = useState<GenerationStatus>({ status: "idle", message: "" });

  const generateTimetable = async () => {
    try {
      setStatus({ status: "loading", message: "🔄 Generating timetable..." });
      
      const response = await api.post("/timetable/generate", {
        name: `Timetable ${new Date().toLocaleString()}`,
        description: "Auto-generated",
      });

      if (response.data.success) {
        setStatus({
          status: "success",
          message: `✅ Timetable generated successfully! (${response.data.slots_generated} periods created)`,
        });
      } else {
        setStatus({
          status: "error",
          message: `❌ Error: ${response.data.message}`,
        });
      }
    } catch (error: any) {
      setStatus({
        status: "error",
        message: `❌ Error: ${error.response?.data?.message || error.message}`,
      });
    }
  };

  const exportTimetable = async (type: "batch" | "teacher", id: number) => {
    try {
      setStatus({ status: "loading", message: `📥 Downloading ${type} timetable...` });
      
      const endpoint = type === "batch" 
        ? `/export/timetable/batch/${id}`
        : `/export/timetable/teacher/${id}`;

      const response = await api.get(endpoint, { responseType: "blob" });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${type}_${id}_timetable.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);

      setStatus({
        status: "success",
        message: `✅ ${type.charAt(0).toUpperCase() + type.slice(1)} timetable downloaded!`,
      });
    } catch (error: any) {
      setStatus({
        status: "error",
        message: `❌ Error: ${error.response?.data?.message || error.message}`,
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Generate Timetable Section */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
        <h2 className="text-2xl font-bold text-blue-900 mb-2">⏱️ Generate Timetable</h2>
        <p className="text-blue-700 mb-4">Create an automated timetable for all classes and teachers</p>
        
        <button
          onClick={generateTimetable}
          disabled={status.status === "loading"}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center gap-2"
        >
          {status.status === "loading" ? (
            <>
              <span className="animate-spin">⏳</span>
              Generating...
            </>
          ) : (
            <>
              📊 Generate Timetable
            </>
          )}
        </button>

        {status.message && (
          <div
            className={`mt-4 p-3 rounded text-sm font-medium ${
              status.status === "success"
                ? "bg-green-100 text-green-800 border border-green-300"
                : status.status === "error"
                ? "bg-red-100 text-red-800 border border-red-300"
                : "bg-blue-100 text-blue-800 border border-blue-300"
            }`}
          >
            {status.message}
          </div>
        )}
      </div>

      {/* Export Timetables Section */}
      <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-200">
        <h2 className="text-2xl font-bold text-purple-900 mb-2">📥 Download Timetables</h2>
        <p className="text-purple-700 mb-4">Export timetables as PDF for classes and individual teachers</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Class Timetable Export */}
          <div className="bg-white p-4 rounded-lg border border-purple-200">
            <h3 className="font-semibold text-purple-900 mb-3">📚 Class Timetable</h3>
            <button
              onClick={() => exportTimetable("batch", 1)}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded transition"
            >
              📄 Download Class 1A PDF
            </button>
            <p className="text-xs text-gray-600 mt-2">Exports complete timetable for a class with all students</p>
          </div>

          {/* Teacher Timetable Export */}
          <div className="bg-white p-4 rounded-lg border border-purple-200">
            <h3 className="font-semibold text-purple-900 mb-3">👨‍🏫 Teacher Timetable</h3>
            <button
              onClick={() => exportTimetable("teacher", 1)}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 px-4 rounded transition"
            >
              📄 Download Teacher 1 PDF
            </button>
            <p className="text-xs text-gray-600 mt-2">Exports schedule for an individual teacher</p>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm">
        <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Timetable Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
            <p className="text-2xl font-bold text-blue-600">73</p>
            <p className="text-sm text-gray-600">Classes</p>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
            <p className="text-2xl font-bold text-purple-600">75</p>
            <p className="text-sm text-gray-600">Teachers</p>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
            <p className="text-2xl font-bold text-green-600">2,800+</p>
            <p className="text-sm text-gray-600">Students</p>
          </div>
          <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg">
            <p className="text-2xl font-bold text-orange-600">20+</p>
            <p className="text-sm text-gray-600">Subjects</p>
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="bg-gradient-to-r from-amber-50 to-amber-100 rounded-lg p-6 border-2 border-amber-200">
        <h3 className="font-bold text-amber-900 mb-2">💡 How to Use</h3>
        <ol className="text-sm text-amber-800 space-y-1 list-decimal list-inside">
          <li>Click "Generate Timetable" to create an automated schedule</li>
          <li>Download PDF timetables for classes or individual teachers</li>
          <li>PDFs are ready to print and distribute to stakeholders</li>
          <li>Use for academic planning and resource allocation</li>
        </ol>
      </div>
    </div>
  );
}
