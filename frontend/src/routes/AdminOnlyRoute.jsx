import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function AdminOnlyRoute({ children }) {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (!user?.is_superuser) {
    return (
      <div className="status-card alert" role="alert">
        <p><strong>Brak uprawnień.</strong> Ta sekcja jest dostępna tylko dla administratora.</p>
        <div className="actions">
          <button type="button" className="secondary-button" onClick={() => navigate(-1)}>
            &larr; Wróć
          </button>
          <button type="button" className="primary-button" onClick={() => navigate("/account/verify")}>
            Przejdź do formularza
          </button>
        </div>
      </div>
    );
  }

  return children;
}

