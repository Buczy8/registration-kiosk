import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage({ onBack, onSuccess }) {
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const profile = await login({ email, password });
      if (onSuccess) {
        onSuccess(profile);
      }
    } catch (err) {
      setError(err.message || "Nieprawidłowy adres e-mail lub hasło.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="form-card auth-card">
        <h2>Logowanie</h2>

        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Adres e-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="np. jan.kowalski@example.com"
            />
          </div>

          <div className="field">
            <label htmlFor="password">Hasło</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="actions auth-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={onBack}
              disabled={loading}
            >
              &larr; Wróć
            </button>
            <button
              type="submit"
              className="primary-button"
              disabled={loading}
              style={{ minWidth: "140px" }}
            >
              {loading ? "Logowanie..." : "Zaloguj się"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
