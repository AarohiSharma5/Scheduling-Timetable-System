import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/Common";
import DashboardPage from "./pages/DashboardPage";
import SetupPage from "./pages/SetupPage";
import CurriculumPage from "./pages/CurriculumPage";
import ReviewPage from "./pages/ReviewPage";

const App: React.FC = () => {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/plans/:id/setup" element={<SetupPage />} />
          <Route path="/plans/:id/curriculum" element={<CurriculumPage />} />
          <Route path="/plans/:id/review" element={<ReviewPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;
