import React, { useState } from "react";
import { useAuthStore } from "../stores/authStore";
import TeacherManagement from "../components/TeacherManagement";
import StudentManagement from "../components/StudentManagement";
import BatchManagement from "../components/BatchManagement";
import RoomManagement from "../components/RoomManagement";
import TeachingGroups from "../components/TeachingGroups";
import ClassPeriodConfig from "../components/ClassPeriodConfig";
import SubjectManagement from "../components/SubjectManagement";
import ConfigurationForm from "../components/ConfigurationForm";
import TimetableGenerator from "../components/TimetableGenerator";
import LeaveManagement from "../components/LeaveManagement";
import NotificationsCenter from "../components/NotificationsCenter";
import PinnedSlotsManager from "../components/PinnedSlotsManager";
import ChargeManagement from "../components/ChargeManagement";
import InvitationsPanel from "../components/InvitationsPanel";
import AttendancePanel from "../components/AttendancePanel";
import ExamsPanel from "../components/ExamsPanel";
import AnnouncementsPanel from "../components/AnnouncementsPanel";
import ParentsPanel from "../components/ParentsPanel";
import FeesPanel from "../components/FeesPanel";
import AssignmentsPanel from "../components/AssignmentsPanel";
import CalendarPanel from "../components/CalendarPanel";
import LibraryPanel from "../components/LibraryPanel";
import TransportPanel from "../components/TransportPanel";
import InventoryPanel from "../components/InventoryPanel";
import AnalyticsPanel from "../components/AnalyticsPanel";
import MessagesPanel from "../components/MessagesPanel";

type Tab = "timetable" | "analytics" | "students" | "attendance" | "exams" | "homework" | "fees" | "announcements" | "messages" | "calendar" | "library" | "transport" | "inventory" | "teachers" | "parents" | "batches" | "rooms" | "groups" | "classperiods" | "subjects" | "charges" | "pinned" | "invitations" | "leaves" | "notifications" | "config";

const tabs: Record<Tab, { icon: string; label: string }> = {
  timetable: { icon: "📊", label: "Timetable" },
  analytics: { icon: "📈", label: "Analytics" },
  students: { icon: "👥", label: "Students" },
  attendance: { icon: "📝", label: "Attendance" },
  exams: { icon: "🧪", label: "Exams" },
  homework: { icon: "📒", label: "Homework" },
  fees: { icon: "💳", label: "Fees" },
  announcements: { icon: "📣", label: "Announcements" },
  messages: { icon: "💬", label: "Messages" },
  calendar: { icon: "🗓️", label: "Calendar" },
  library: { icon: "📚", label: "Library" },
  transport: { icon: "🚌", label: "Transport" },
  inventory: { icon: "📦", label: "Inventory" },
  teachers: { icon: "👨‍🏫", label: "Teachers" },
  parents: { icon: "👪", label: "Parents" },
  batches: { icon: "📚", label: "Batches" },
  rooms: { icon: "🏫", label: "Rooms" },
  groups: { icon: "🧩", label: "Teaching Groups" },
  classperiods: { icon: "🗓️", label: "Class Periods" },
  subjects: { icon: "📖", label: "Subjects" },
  charges: { icon: "🏅", label: "Departments" },
  pinned: { icon: "📌", label: "Fixed Periods" },
  invitations: { icon: "✉️", label: "Invitations" },
  leaves: { icon: "🔁", label: "Substitutes" },
  notifications: { icon: "🔔", label: "Notifications" },
  config: { icon: "⚙️", label: "Configuration" },
};

export default function AdminPage() {
  const { user, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>("timetable");

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-slate-900">📊 Admin Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">👤 {user?.name}</span>
            <button
              onClick={() => logout()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex gap-1 overflow-x-auto">
          {(Object.entries(tabs) as [Tab, typeof tabs[Tab]][]).map(([key, { icon, label }]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-3 text-sm font-medium flex items-center gap-2 border-b-2 whitespace-nowrap transition ${
                activeTab === key
                  ? "border-blue-600 text-blue-700 bg-blue-50"
                  : "border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <span className="text-base">{icon}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md p-6">
          {activeTab === "timetable" && <TimetableGenerator />}
          {activeTab === "analytics" && <AnalyticsPanel />}
          {activeTab === "students" && <StudentManagement />}
          {activeTab === "attendance" && <AttendancePanel />}
          {activeTab === "exams" && <ExamsPanel />}
          {activeTab === "homework" && <AssignmentsPanel />}
          {activeTab === "fees" && <FeesPanel />}
          {activeTab === "announcements" && <AnnouncementsPanel />}
          {activeTab === "messages" && <MessagesPanel />}
          {activeTab === "calendar" && <CalendarPanel />}
          {activeTab === "library" && <LibraryPanel />}
          {activeTab === "transport" && <TransportPanel />}
          {activeTab === "inventory" && <InventoryPanel />}
          {activeTab === "parents" && <ParentsPanel />}
          {activeTab === "teachers" && <TeacherManagement />}
          {activeTab === "batches" && <BatchManagement />}
          {activeTab === "rooms" && <RoomManagement />}
          {activeTab === "groups" && <TeachingGroups />}
          {activeTab === "classperiods" && <ClassPeriodConfig />}
          {activeTab === "subjects" && <SubjectManagement />}
          {activeTab === "charges" && <ChargeManagement />}
          {activeTab === "pinned" && <PinnedSlotsManager />}
          {activeTab === "invitations" && <InvitationsPanel />}
          {activeTab === "leaves" && <LeaveManagement mode="substitute" />}
          {activeTab === "notifications" && <NotificationsCenter />}
          {activeTab === "config" && <ConfigurationForm />}
        </div>
      </main>
    </div>
  );
}
