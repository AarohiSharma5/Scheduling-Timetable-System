import React, { useState, useEffect } from "react";
import { api } from "../api";

interface Notification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
  action_url?: string;
}

export default function NotificationsCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await api.get("/api/notifications");
      setNotifications(response.data);

      // Get unread count
      const unreadResponse = await api.get("/api/notifications/unread-count");
      setUnreadCount(unreadResponse.data.unread_count);
    } catch (error) {
      console.error("Error fetching notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId: number) => {
    try {
      await api.post(`/api/notifications/${notificationId}/mark-read`);
      setMessage("✅ Marked as read");
      fetchNotifications();
    } catch (error) {
      console.error("Error marking as read:", error);
    }
  };

  const markAllAsRead = async () => {
    try {
      setMessage("⏳ Marking all as read...");
      await api.post("/api/notifications/mark-all-read");
      setMessage("✅ All marked as read");
      fetchNotifications();
    } catch (error) {
      console.error("Error marking all as read:", error);
      setMessage("❌ Error marking all as read");
    }
  };

  const deleteNotification = async (notificationId: number) => {
    try {
      await api.delete(`/api/notifications/${notificationId}`);
      setMessage("✅ Notification deleted");
      fetchNotifications();
    } catch (error) {
      console.error("Error deleting notification:", error);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "leave_approved":
        return "✅";
      case "leave_rejected":
        return "❌";
      case "teacher_substituted":
        return "🔄";
      case "timetable_generated":
        return "📊";
      case "class_timing_changed":
        return "⏰";
      case "teacher_absent":
        return "🚨";
      default:
        return "🔔";
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case "leave_approved":
        return "from-green-50 to-green-100 border-green-200";
      case "leave_rejected":
        return "from-red-50 to-red-100 border-red-200";
      case "teacher_substituted":
        return "from-blue-50 to-blue-100 border-blue-200";
      case "timetable_generated":
        return "from-purple-50 to-purple-100 border-purple-200";
      case "teacher_absent":
        return "from-orange-50 to-orange-100 border-orange-200";
      default:
        return "from-gray-50 to-gray-100 border-gray-200";
    }
  };

  const displayNotifications = filter === "unread" ? notifications.filter((n) => !n.is_read) : notifications;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg p-6 text-white">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold flex items-center gap-2">
              🔔 Notifications
            </h2>
            <p className="text-blue-100 mt-2">
              You have {unreadCount} unread notification{unreadCount !== 1 ? "s" : ""}
            </p>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllAsRead}
              className="bg-white hover:bg-blue-50 text-blue-600 font-bold py-2 px-4 rounded-lg"
            >
              Mark All as Read
            </button>
          )}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`p-4 rounded-lg border ${
            message.includes("✅")
              ? "bg-green-50 border-green-200 text-green-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          {message}
        </div>
      )}

      {/* Filter Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 rounded font-medium transition ${
            filter === "all"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          All Notifications
        </button>
        <button
          onClick={() => setFilter("unread")}
          className={`px-4 py-2 rounded font-medium transition ${
            filter === "unread"
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          Unread ({unreadCount})
        </button>
        <button
          onClick={fetchNotifications}
          className="ml-auto px-4 py-2 rounded font-medium bg-gray-200 text-gray-700 hover:bg-gray-300 transition"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Notifications List */}
      {loading ? (
        <p className="text-gray-600 text-center py-8">⏳ Loading notifications...</p>
      ) : displayNotifications.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-2xl mb-2">📭</p>
          <p className="text-gray-600">
            {filter === "unread" ? "No unread notifications" : "No notifications yet"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {displayNotifications.map((notification) => (
            <div
              key={notification.id}
              className={`bg-gradient-to-r ${getNotificationColor(
                notification.notification_type
              )} rounded-lg p-4 border-2 transition hover:shadow-md ${
                !notification.is_read ? "ring-2 ring-blue-400" : ""
              }`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{getNotificationIcon(notification.notification_type)}</span>
                    <h3 className="font-bold text-gray-900">{notification.title}</h3>
                    {!notification.is_read && (
                      <span className="ml-auto bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded">
                        NEW
                      </span>
                    )}
                  </div>
                  <p className="text-gray-700 text-sm mb-2">{notification.message}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(notification.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-3 flex gap-2">
                {!notification.is_read && (
                  <button
                    onClick={() => markAsRead(notification.id)}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3 py-1 rounded"
                  >
                    Mark as Read
                  </button>
                )}
                {notification.action_url && (
                  <a
                    href={notification.action_url}
                    className="bg-green-600 hover:bg-green-700 text-white text-xs font-medium px-3 py-1 rounded"
                  >
                    View Details
                  </a>
                )}
                <button
                  onClick={() => deleteNotification(notification.id)}
                  className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium px-3 py-1 rounded"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Information Card */}
      <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
        <h3 className="font-bold text-blue-900 mb-2">💡 About Notifications</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>✅ Leave Approved - Your leave request has been approved</li>
          <li>❌ Leave Rejected - Your leave request was rejected</li>
          <li>🔄 Teacher Substituted - A substitute has been assigned for a class</li>
          <li>📊 Timetable Generated - New timetable has been created</li>
          <li>⏰ Class Timing Changed - Schedule for your class has been modified</li>
          <li>🚨 Teacher Absent - A teacher has been marked absent</li>
        </ul>
      </div>
    </div>
  );
}
