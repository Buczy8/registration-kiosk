import { useEffect, useState } from "react";
import { createGuestSubmission, createAccountSubmission, getActiveForm } from "./api/kiosk.js";
import GuestRegistrationForm from "./components/GuestRegistrationForm.jsx";
import SubmissionResult from "./components/SubmissionResult.jsx";
import GuardianPlaceholder from "./pages/GuardianPlaceholder.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import RoleVehicleSelect from "./pages/RoleVehicleSelect.jsx";
import StartScreen from "./pages/StartScreen.jsx";
import VerifyDataForm from "./pages/VerifyDataForm.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import { useIdleLogout } from "./hooks/useIdleLogout.js";

export default function App() {
  const { isAuthenticated, logout, isInitializing, user, token } = useAuth();

  const [view, setView] = useState("start");
  const [accountStep, setAccountStep] = useState("role-select");
  const [selectedRole, setSelectedRole] = useState(null);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [submissions, setSubmissions] = useState(null);
  const [submissionIsAccount, setSubmissionIsAccount] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [startInfoMessage, setStartInfoMessage] = useState(null);

  function resetAccountFlow() {
    setAccountStep("role-select");
    setSelectedRole(null);
    setSelectedVehicle(null);
    setSubmitError(null);
  }

  function handleLogout() {
    logout();
    setView("start");
    resetAccountFlow();
    setSubmissions(null);
    setSubmissionIsAccount(false);
  }

  useIdleLogout(() => {
    if (isAuthenticated) {
      handleLogout();
      setStartInfoMessage("Sesja wygasła ze względów bezpieczeństwa.");
    }
  });

  useEffect(() => {
    if (!startInfoMessage) {
      return undefined;
    }

    const hideMessageTimer = setTimeout(() => {
      setStartInfoMessage(null);
    }, 5000);

    return () => clearTimeout(hideMessageTimer);
  }, [startInfoMessage]);

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

  async function handleGuestSubmit(payloadOrArray) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payloads = Array.isArray(payloadOrArray) ? payloadOrArray : [payloadOrArray];
      const results = [];
      for (const payload of payloads) {
        results.push(await createGuestSubmission(payload));
      }
      setSubmissionIsAccount(false);
      setSubmissions(results);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAccountSubmit(payload) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await createAccountSubmission(payload, token);
      setSubmissionIsAccount(true);
      setSubmissions([result]);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleGuestNewSubmission() {
    setSubmissions(null);
    setSubmitError(null);
    setView("start");
  }

  function handleAccountNewForm() {
    setSubmissions(null);
    setSubmitError(null);
    resetAccountFlow();
  }

  function handleRoleVehicleContinue({ role, vehicle }) {
    setSelectedRole(role);
    setSelectedVehicle(vehicle);
    if (role === "legal_guardian") {
      setAccountStep("guardian-placeholder");
      return;
    }
    setAccountStep("verify");
  }

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
    return (
      <SubmissionResult
        submissions={submissions}
        isAccountMode={submissionIsAccount}
        onNewSubmission={handleGuestNewSubmission}
        onNewForm={handleAccountNewForm}
        onLogout={handleLogout}
      />
    );
  }

  if (!isAuthenticated) {
    if (view === "start") {
      return (
        <StartScreen
          infoMessage={startInfoMessage}
          onGuest={() => setView("guest")}
          onLogin={() => setView("login")}
          onRegister={() => setView("register")}
        />
      );
    }
    if (view === "login") {
      return <LoginPage onBack={() => setView("start")} />;
    }
    if (view === "register") {
      return <RegisterPage onBack={() => setView("start")} />;
    }

    return (
      <div className="app-container">
        <div style={{ marginBottom: "15px" }}>
          <button className="secondary-button" type="button" onClick={() => setView("start")}>
            &larr; Wróć
          </button>
        </div>
        <GuestRegistrationForm
          form={form}
          onSubmit={handleGuestSubmit}
          submitting={submitting}
          submitError={submitError}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      {user && (
        <div
          className="user-bar"
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "10px",
            backgroundColor: "#f0f0f0",
            marginBottom: "20px",
            borderRadius: "4px",
          }}
        >
          <span>
            Zalogowano jako: <strong>{user.email}</strong>
          </span>
          <button
            type="button"
            onClick={handleLogout}
            style={{
              background: "#dc3545",
              color: "#fff",
              border: "none",
              padding: "5px 10px",
              borderRadius: "3px",
              cursor: "pointer",
            }}
          >
            Wyloguj się
          </button>
        </div>
      )}

      {accountStep === "role-select" && (
        <RoleVehicleSelect
          onContinue={handleRoleVehicleContinue}
          defaultRole={user?.last_participant_role || ""}
          defaultVehicle={user?.last_vehicle_type || ""}
        />
      )}

      {accountStep === "guardian-placeholder" && (
        <GuardianPlaceholder onBack={() => setAccountStep("role-select")} />
      )}

      {accountStep === "verify" && selectedRole && selectedVehicle && (
        <VerifyDataForm
          form={form}
          role={selectedRole}
          vehicleType={selectedVehicle}
          token={token}
          onSubmit={handleAccountSubmit}
          onBack={() => setAccountStep("role-select")}
          submitting={submitting}
          submitError={submitError}
        />
      )}
    </div>
  );
}
