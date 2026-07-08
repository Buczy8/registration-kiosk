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
    <div className="login-screen" style={{ padding: "24px 0" }}>
      <div className="form-card" style={{ maxWidth: "480px", margin: "0 auto" }}>
        <h2 style={{ marginTop: 0, marginBottom: "20px", fontSize: "1.5rem" }}>Logowanie</h2>

        {error && (
          <div className="alert" role="alert" style={{ marginBottom: "16px" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "20px" }}>
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
              style={{ padding: "14px", fontSize: "1.1rem" }}
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
              style={{ padding: "14px", fontSize: "1.1rem" }}
            />
          </div>

          <div className="actions" style={{ marginTop: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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