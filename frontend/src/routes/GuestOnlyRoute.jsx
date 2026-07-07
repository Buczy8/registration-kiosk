import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function GuestOnlyRoute({ children }) {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <Navigate to="/account/role" replace />;
  }
  return children;
}
