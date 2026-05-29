import React, { useState, useEffect } from "react";
import { api } from "../api";

interface LeaveRequest {
  id: number;
  teacher_name: string;
  leave_date: string;
  reason: string;
  leave_type: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  substitute_teacher_id?: number;
  substitute_teacher_name?: string;
}

interface Substitute {
  id: number;
  name: string;
  available_score: number;
  reason: string;
}

export default function LeaveManagement() {
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);
  const [substitutes, setSubstitutes] = useState<Substitute[]>([]);
  const [loadingSubstitutes, setLoadingSubstitutes] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchLeaves();
  }, []);

  const fetchLeaves = async () => {
    try {
      setLoading(true);
      const response = await api.get("/leaves");
      setLeaves(response.data);
    } catch (error) {
      console.error("Error fetching leaves:", error);
      setMessage("❌ Error loading leave requests");
    } finally {
      setLoading(false);
    }
  };

  const getSubstitutes = async (leaveId: number) => {
    try {
      setLoadingSubstitutes(true);
      const response = await api.get(`/leaves/${leaveId}/substitute-options`);
      setSubstitutes(response.data.available_substitutes || []);
      setMessage("✅ Available substitutes loaded");
    } catch (error) {
      console.error("Error fetching substitutes:", error);
      setMessage("❌ Error loading substitutes");
    } finally {
      setLoadingSubstitutes(false);
    }
  };

  const approveLeavewithSubstitute = async (leaveId: number, substituteId: number) => {
    try {
      setMessage("⏳ Approving leave...");
      const response = await api.post(`/leaves/${leaveId}/approve`, {
        substitute_teacher_id: substituteId,
        auto_adjust: true,
      });

      if (response.data.success) {
        setMessage("✅ Leave approved successfully!");
        setSelectedLeave(null);
        fetchLeaves();
      }
    } catch (error: any) {
      setMessage(`❌ Error: ${error.response?.data?.message || error.message}`);
    }
  };

  const rejectLeave = async (leaveId: number) => {
    try {
      setMessage("⏳ Rejecting leave...");
      const response = await api.post(`/leaves/${leaveId}/reject`, {
        rejection_reason: "Not approved by admin",
      });

      if (response.data.success) {
        setMessage("✅ Leave rejected!");
        setSelectedLeave(null);
        fetchLeaves();
      }
    } catch (error: any) {
      setMessage(`❌ Error: ${error.response?.data?.message || error.message}`);
    }
  };

  const markTeacherAbsent = async (teacherId: number) => {
    try {
      setMessage("⏳ Marking teacher absent...");
      const response = await api.post(`/teachers/${teacherId}/mark-absent`, {
        date: new Date().toISOString().split("T")[0],
        reason: "Unannounced absence",
      });

      if (response.data.success) {
        setMessage("✅ Teacher marked absent. Substitute auto-assigned!");
        fetchLeaves();
      }
    } catch (error: any) {
      setMessage(`❌ Error: ${error.response?.data?.message || error.message}`);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-green-100 text-green-800";
      case "REJECTED":
        return "bg-red-100 text-red-800";
      default:
        return "bg-yellow-100 text-yellow-800";
    }
  };

  return (
    <div className="space-y-6">
      {/* Message */}
      {message && (
        <div
          className={`p-4 rounded-lg border ${
            message.includes("✅")
              ? "bg-green-50 border-green-200 text-green-800"
              : message.includes("❌")
              ? "bg-red-50 border-red-200 text-red-800"
              : "bg-blue-50 border-blue-200 text-blue-800"
          }`}
        >
          {message}
        </div>
      )}

      {/* Leave Request List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">📋 Leave Requests</h2>
          <button
            onClick={fetchLeaves}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium"
          >
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <p className="text-gray-600">Loading leave requests...</p>
        ) : leaves.length === 0 ? (
          <p className="text-gray-600">No leave requests yet</p>
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
                  <th className="px-4 py-2 text-left font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leaves.map((leave) => (
                  <tr key={leave.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{leave.teacher_name}</td>
                    <td className="px-4 py-2">{leave.leave_date}</td>
                    <td className="px-4 py-2">{leave.reason}</td>
                    <td className="px-4 py-2">{leave.leave_type}</td>
                    <td className="px-4 py-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadge(leave.status)}`}>
                        {leave.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {leave.status === "PENDING" ? (
                        <button
                          onClick={() => {
                            setSelectedLeave(leave);
                            getSubstitutes(leave.id);
                          }}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs font-medium"
                        >
                          Review
                        </button>
                      ) : (
                        <span className="text-gray-500">Done</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Selected Leave Detail & Substitution */}
      {selectedLeave && (
        <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-200">
          <h3 className="text-xl font-bold text-blue-900 mb-4">
            ✅ Review Leave Request from {selectedLeave.teacher_name}
          </h3>

          <div className="bg-white p-4 rounded-lg mb-4 space-y-2">
            <p>
              <span className="font-semibold">Date:</span> {selectedLeave.leave_date}
            </p>
            <p>
              <span className="font-semibold">Reason:</span> {selectedLeave.reason}
            </p>
            <p>
              <span className="font-semibold">Type:</span> {selectedLeave.leave_type}
            </p>
          </div>

          {loadingSubstitutes ? (
            <p className="text-blue-700">⏳ Loading available substitutes...</p>
          ) : substitutes.length === 0 ? (
            <p className="text-red-700">❌ No substitutes available</p>
          ) : (
            <div className="space-y-3">
              <p className="font-semibold text-blue-900">Select Substitute Teacher:</p>
              {substitutes.map((sub) => (
                <div key={sub.id} className="flex justify-between items-center bg-white p-3 rounded-lg border border-blue-200">
                  <div>
                    <p className="font-medium text-gray-900">{sub.name}</p>
                    <p className="text-xs text-gray-600">{sub.reason}</p>
                    <p className="text-xs font-semibold text-blue-600">Score: {(sub.available_score * 100).toFixed(0)}%</p>
                  </div>
                  <button
                    onClick={() => approveLeavewithSubstitute(selectedLeave.id, sub.id)}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium"
                  >
                    Approve
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => rejectLeave(selectedLeave.id)}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium"
            >
              Reject
            </button>
            <button
              onClick={() => setSelectedLeave(null)}
              className="bg-gray-400 hover:bg-gray-500 text-white px-4 py-2 rounded font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Emergency Actions */}
      <div className="bg-gradient-to-r from-red-50 to-red-100 rounded-lg p-6 border-2 border-red-200">
        <h3 className="text-xl font-bold text-red-900 mb-2">🚨 Emergency Actions</h3>
        <p className="text-red-700 mb-4">Mark a teacher as absent immediately (auto-assigns substitute)</p>
        <button
          onClick={() => markTeacherAbsent(1)}
          className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium"
        >
          Mark Teacher Absent Today
        </button>
      </div>
    </div>
  );
}
