import React, { useState, useEffect } from "react";
import { api } from "../api";

interface Student {
  id: number;
  student_id: string;
  admission_no: string;
  first_name: string;
  last_name: string;
  gender: string;
  date_of_birth: string;
  class_grade: string;
  section: string;
  roll_no: number;
  house_name: string;
  contact_number: string;
  status: string;
}

export default function StudentManagement() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClass, setSelectedClass] = useState("7");
  const [selectedSection, setSelectedSection] = useState("A");
  const [message, setMessage] = useState("");

  const classes = [
    "Nursery",
    "LKG",
    "UKG",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11 Science",
    "11 Commerce",
    "11 Humanities",
    "12 Science",
    "12 Commerce",
    "12 Humanities",
  ];
  const sections = ["A", "B", "C", "D", "E"];

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const response = await api.get(
        `/students?class=${selectedClass}&section=${selectedSection}`
      );
      setStudents(response.data);
      setMessage(`✅ Loaded ${response.data.length} students`);
    } catch (error: any) {
      console.error("Error fetching students:", error);
      setMessage(`❌ ${error.response?.data?.message || "Error loading students"}`);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [selectedClass, selectedSection]);

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
        <h2 className="text-2xl font-bold text-blue-900 mb-4">👥 Student List</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-semibold text-blue-900 mb-2">
              Class
            </label>
            <select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-blue-900 mb-2">
              Section
            </label>
            <select
              value={selectedSection}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {sections.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-blue-900 mb-2">
              &nbsp;
            </label>
            <button
              onClick={fetchStudents}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 rounded-lg"
            >
              🔄 Load Students
            </button>
          </div>
        </div>

        {message && (
          <div
            className={`p-3 rounded text-sm font-medium ${
              message.includes("✅")
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {message}
          </div>
        )}
      </div>

      {/* Students Table */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          Class {selectedClass} - Section {selectedSection} ({students.length} students)
        </h3>

        {loading ? (
          <p className="text-gray-600 text-center py-8">⏳ Loading students...</p>
        ) : students.length === 0 ? (
          <p className="text-gray-600 text-center py-8">No students found for this class</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Roll No</th>
                  <th className="px-4 py-3 text-left font-semibold">Student ID</th>
                  <th className="px-4 py-3 text-left font-semibold">Name</th>
                  <th className="px-4 py-3 text-left font-semibold">Gender</th>
                  <th className="px-4 py-3 text-left font-semibold">DOB</th>
                  <th className="px-4 py-3 text-left font-semibold">House</th>
                  <th className="px-4 py-3 text-left font-semibold">Contact</th>
                  <th className="px-4 py-3 text-left font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student, idx) => (
                  <tr key={student.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{student.roll_no}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{student.student_id}</td>
                    <td className="px-4 py-3 font-medium">
                      {student.first_name} {student.last_name}
                    </td>
                    <td className="px-4 py-3">{student.gender === "M" ? "👦" : "👧"}</td>
                    <td className="px-4 py-3 text-sm">
                      {new Date(student.date_of_birth).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                        {student.house_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs">{student.contact_number}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          student.status === "Active"
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {student.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Statistics */}
      {students.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <p className="text-2xl font-bold text-blue-600">{students.length}</p>
            <p className="text-sm text-gray-600">Total Students</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
            <p className="text-2xl font-bold text-purple-600">
              {students.filter((s) => s.gender === "M").length}
            </p>
            <p className="text-sm text-gray-600">Boys</p>
          </div>
          <div className="bg-pink-50 rounded-lg p-4 border border-pink-200">
            <p className="text-2xl font-bold text-pink-600">
              {students.filter((s) => s.gender === "F").length}
            </p>
            <p className="text-sm text-gray-600">Girls</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 border border-green-200">
            <p className="text-2xl font-bold text-green-600">
              {students.filter((s) => s.status === "Active").length}
            </p>
            <p className="text-sm text-gray-600">Active</p>
          </div>
        </div>
      )}
    </div>
  );
}
