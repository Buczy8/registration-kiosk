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

const SCREENS = {
  START: "start",
  LOGIN: "login",
  REGISTER: "register",
  GUEST: "guest",
  ROLE_SELECT: "role-select",
  VERIFY: "verify",
  RESULT: "result",
};

export default function App() {
  const { isAuthenticated, logout, isInitializing, user, token } = useAuth();

  const [screen, setScreen] = useState(SCREENS.START);
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

  function resetAccountSelection() {
    setSelectedRole(null);
    setSelectedVehicle(null);
    setSubmitError(null);
  }

  function handleLogout() {
    logout();
    setScreen(SCREENS.START);
    resetAccountSelection();
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
    const publicScreens = [SCREENS.START, SCREENS.LOGIN, SCREENS.REGISTER, SCREENS.GUEST];
    const accountScreens = [SCREENS.ROLE_SELECT, SCREENS.VERIFY];

    if (isAuthenticated && publicScreens.includes(screen)) {
      setScreen(SCREENS.ROLE_SELECT);
    }

    if (!isAuthenticated && accountScreens.includes(screen)) {
      setScreen(SCREENS.START);
      setSelectedRole(null);
      setSelectedVehicle(null);
    }
  }, [isAuthenticated, screen]);

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
      setScreen(SCREENS.RESULT);
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
      setScreen(SCREENS.RESULT);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleGuestNewSubmission() {
    setSubmissions(null);
    setSubmitError(null);
    setScreen(SCREENS.START);
  }

  function handleAccountNewForm() {
    setSubmissions(null);
    setSubmitError(null);
    resetAccountSelection();
    setScreen(SCREENS.ROLE_SELECT);
  }

  function handleRoleVehicleContinue({ role, vehicle }) {
    setSelectedRole(role);
    setSelectedVehicle(vehicle);
    setScreen(SCREENS.VERIFY);
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

  if (screen === SCREENS.RESULT && submissions) {
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

  if (!isAuthenticated && screen === SCREENS.START) {
    return (
      <StartScreen
        infoMessage={startInfoMessage}
        onGuest={() => setScreen(SCREENS.GUEST)}
        onLogin={() => setScreen(SCREENS.LOGIN)}
        onRegister={() => setScreen(SCREENS.REGISTER)}
      />
    );
  }

  if (!isAuthenticated && screen === SCREENS.LOGIN) {
    return <LoginPage onBack={() => setScreen(SCREENS.START)} />;
  }

  if (!isAuthenticated && screen === SCREENS.REGISTER) {
    return <RegisterPage onBack={() => setScreen(SCREENS.START)} />;
  }

  if (!isAuthenticated && screen === SCREENS.GUEST) {
    return (
      <div className="app-container">
        <div style={{ marginBottom: "15px" }}>
          <button className="secondary-button" type="button" onClick={() => setScreen(SCREENS.START)}>
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

      {screen === SCREENS.ROLE_SELECT && (
        <RoleVehicleSelect
          onContinue={handleRoleVehicleContinue}
          defaultRole={user?.last_participant_role || ""}
          defaultVehicle={user?.last_vehicle_type || ""}
        />
      )}

      {screen === SCREENS.VERIFY && selectedRole === "legal_guardian" && (
        <GuardianPlaceholder onBack={() => setScreen(SCREENS.ROLE_SELECT)} />
      )}

      {screen === SCREENS.VERIFY && selectedRole && selectedVehicle && selectedRole !== "legal_guardian" && (
        <VerifyDataForm
          form={form}
          role={selectedRole}
          vehicleType={selectedVehicle}
          token={token}
          onSubmit={handleAccountSubmit}
          onBack={() => setScreen(SCREENS.ROLE_SELECT)}
          submitting={submitting}
          submitError={submitError}
        />
      )}
    </div>
  );
}
