import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import CaseDetail from "@/pages/CaseDetail";
import NewCase from "@/pages/NewCase";
import ReportEditor from "@/pages/ReportEditor";

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("access_token");
  return token ? children : <Navigate to="/" replace />;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId"
            element={
              <ProtectedRoute>
                <CaseDetail />
              </ProtectedRoute>
            }
          />
          <Route 
            path="/embed/case/:caseId" 
            element={
              <CaseDetail embedMode />
            } 
          />
          <Route
            path="/cases/new"
            element={
              <ProtectedRoute>
                <NewCase />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/report"
            element={
              <ProtectedRoute>
                <ReportEditor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cases/:caseId/report/:reportId"
            element={
              <ProtectedRoute>
                <ReportEditor />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
