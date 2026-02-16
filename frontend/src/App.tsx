import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/login"
import Home from "./pages/Home";
import Profile from "./users/profile";
import InternDetail from "./pages/InternDetail";


export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route path="/login" element={<Login />} />
      <Route path="/profile" element={<Profile />} />

      <Route path="/home" element={<Home />} />
      <Route path="/intern/:id" element={<InternDetail />} />

      <Route path="*" element={<div style={{ padding: 16 }}>404 Not Found</div>} />
    </Routes>
  );
}
