import { useEffect, useState } from "react";
import { createGuestSubmission, createAccountSubmission, getActiveForm } from "./api/kiosk.js";
import GuestRegistrationForm from "./components/GuestRegistrationForm.jsx";
import SubmissionResult from "./components/SubmissionResult.jsx";
import StartScreen from "./pages/StartScreen.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import { useIdleLogout } from "./hooks/useIdleLogout.js";

export default function App() {
  const { isAuthenticated, logout, isInitializing, user, token } = useAuth();

  const [view, setView] = useState("start");
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [submissions, setSubmissions] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useIdleLogout(() => {
    if (isAuthenticated) {
      logout();
      alert("Sesja wygasła ze względów bezpieczeństwa.");
      setView("start");
    }
  });

  useEffect(() => {
    let cancelled = false;

    async function loadForm() {
      setLoading(true);
      setLoadError(null);
      try {
        const activeForm = await getActiveForm();
        if (!cancelled) {
          setForm(activeForm);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(error.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadForm();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(payloadOrArray) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payloads = Array.isArray(payloadOrArray) ? payloadOrArray : [payloadOrArray];
      const results = [];
      for (const payload of payloads) {
        if (isAuthenticated) {
          results.push(await createAccountSubmission(payload, token));
        } else {
          results.push(await createGuestSubmission(payload));
        }
      }
      setSubmissions(results);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleNewSubmission() {
    setSubmissions(null);
    setSubmitError(null);
    setView("start");
  }

  useEffect(() => {
    if (isAuthenticated && (view === "start" || view === "login")) {
      setView("guest");
    }
  }, [isAuthenticated, view]);

  if (isInitializing) {
    return <p className="status-card">Odtwarzanie sesji...</p>;
  }

  if (loading) {
    return <p className="status-card">Ładowanie formularza...</p>;
  }

  if (loadError) {
    return (
      <div className="status-card alert" role="alert">
        <p>Nie udało się pobrać formularza: {loadError}</p>
        <p>Sprawdź, czy backend działa i czy VITE_KIOSK_TOKEN jest poprawny.</p>
      </div>
    );
  }

  if (submissions) {
    return <SubmissionResult submissions={submissions} onNewSubmission={handleNewSubmission} />;
  }

  if (view === "start" && !isAuthenticated) {
    return (
      <StartScreen
        onGuest={() => setView("guest")}
        onLogin={() => setView("login")}
        onRegister={() => {
          alert("Funkcja rejestracji w przygotowaniu");
        }}
      />
    );
  }
  if (view === "login" && !isAuthenticated) {
    return (
      <LoginPage
        onBack={() => setView("start")}
        onSuccess={() => setView("guest")}
      />
    );
  }

  return (
    <div className="app-container">
      {isAuthenticated && user && (
        <div className="user-bar" style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', backgroundColor: '#f0f0f0', marginBottom: '20px', borderRadius: '4px' }}>
          <span>Zalogowano jako: <strong>{user.email}</strong></span>
          <button onClick={() => { logout(); setView("start"); }} style={{ background: '#dc3545', color: '#fff', border: 'none', padding: '5px 10px', borderRadius: '3px', cursor: 'pointer' }}>
            Wyloguj się
          </button>
        </div>
      )}

      {!isAuthenticated && (
        <div style={{ marginBottom: '15px' }}>
            <button className="secondary-button" onClick={() => setView("start")}>
              &larr; Wróć
            </button>
        </div>
      )}

      <GuestRegistrationForm
        form={form}
        onSubmit={handleSubmit}
        submitting={submitting}
        submitError={submitError}
      />
    </div>
  );
}