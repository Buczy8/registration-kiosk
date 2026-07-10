import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

export default function RegisterPage({ onBack, onSuccess }) {
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Hasło musi mieć co najmniej 8 znaków.");
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setError("Hasło musi zawierać co najmniej jedną wielką literę.");
      return;
    }
    if (!/\d/.test(password)) {
      setError("Hasło musi zawierać co najmniej jedną cyfrę.");
      return;
    }
    if (password !== passwordConfirm) {
      setError("Podane hasła nie są identyczne.");
      return;
    }

    setLoading(true);

    try {
      await register({ email, password, password_confirm: passwordConfirm });

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      if (err.message.includes("już istnieje") || err.message.includes("409")) {
        setError("Rejestracja nie powiodła się. Zweryfikuj podane dane lub spróbuj się zalogować.");
      } else {
        setError(err.message || "Wystąpił nieoczekiwany błąd podczas rejestracji.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen" style={{ padding: "24px 0" }}>
      <div className="form-card" style={{ maxWidth: "480px", margin: "0 auto" }}>
        <h2 style={{ marginTop: 0, marginBottom: "20px", fontSize: "1.5rem" }}>Rejestracja nowego konta</h2>
        <p className="hint" style={{ marginBottom: "16px" }}>
          Podaj adres e-mail i hasło. Pozostałe dane uzupełnisz przy pierwszym formularzu.
        </p>

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
            <label htmlFor="password">Hasło (min. 8 znaków, wielka litera i cyfra)</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              minLength={8}
              style={{ padding: "14px", fontSize: "1.1rem" }}
            />
          </div>

          <div className="field">
            <label htmlFor="passwordConfirm">Powtórz hasło</label>
            <input
              id="passwordConfirm"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              disabled={loading}
              minLength={8}
              style={{ padding: "14px", fontSize: "1.1rem" }}
            />
          </div>

          <div
            className="actions"
            style={{
              marginTop: "8px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
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
              style={{ minWidth: "160px" }}
            >
              {loading ? "Przetwarzanie..." : "Zarejestruj się"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
