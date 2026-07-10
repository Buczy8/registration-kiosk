import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { createAccountSubmission, createGuestSubmission, getActiveForm } from "../api/kiosk.js";
import { createRelatedPerson, createSubmissionForRelatedPerson } from "../api/account.js";
import GuestRegistrationForm from "../components/GuestRegistrationForm.jsx";
import SubmissionResult from "../components/SubmissionResult.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useIdleLogout } from "../hooks/useIdleLogout.js";
import LoginPage from "../pages/LoginPage.jsx";
import RegisterPage from "../pages/RegisterPage.jsx";
import StartScreen from "../pages/StartScreen.jsx";
import AdminHome from "../pages/admin/AdminHome.jsx";
import AdminUsersPage from "../pages/admin/AdminUsersPage.jsx";
import AdminSubmissionsPage from "../pages/admin/AdminSubmissionsPage.jsx";
import AdminSubmissionDetailsPage from "../pages/admin/AdminSubmissionDetailsPage.jsx";
import GuestOnlyRoute from "./GuestOnlyRoute.jsx";
import AdminOnlyRoute from "./AdminOnlyRoute.jsx";
import ProtectedRoute from "./ProtectedRoute.jsx";

export default function AppRouter() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, logout, isInitializing, user, refreshProfile } = useAuth();
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
  const [loadedUserId, setLoadedUserId] = useState(null);
  const defaultUserIdleLogoutSeconds = 30;
  const adminIdleLogoutSeconds = 5 * 60;
  const defaultAuthenticatedRoute = user?.is_superuser ? "/admin" : "/account/verify";

  function resetAccountSelection() {
    setSelectedRole(null);
    setSelectedVehicle(null);
    setSubmitError(null);
  }

  function handleLogout() {
    logout();
    setSubmissions(null);
    setSubmissionIsAccount(false);
    resetAccountSelection();
    navigate("/");
  }

  useIdleLogout({
    enabled: isAuthenticated,
    timeoutSeconds: user?.is_superuser ? adminIdleLogoutSeconds : defaultUserIdleLogoutSeconds,
    onIdle: () => {
      handleLogout();
      setStartInfoMessage("Sesja wygasła ze względów bezpieczeństwa.");
    },
  });

  useEffect(() => {
    if (user) {
      if (user.user_id !== loadedUserId) {
        setSelectedRole(user.last_participant_role || null);
        setSelectedVehicle(user.last_vehicle_type || null);
        setLoadedUserId(user.user_id);
      }
    } else {
      setSelectedRole(null);
      setSelectedVehicle(null);
      setLoadedUserId(null);
    }
  }, [user, loadedUserId]);

  useEffect(() => {
    if (!startInfoMessage) {
      return undefined;
    }
    const timer = setTimeout(() => {
      setStartInfoMessage(null);
    }, 5000);
    return () => clearTimeout(timer);
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

  useEffect(() => {
    document.body.classList.toggle("app-submitting", submitting);
    return () => {
      document.body.classList.remove("app-submitting");
    };
  }, [submitting]);

  useEffect(() => {
    if (location.pathname !== "/result") {
      return undefined;
    }

    const frameId = requestAnimationFrame(() => {
      setSubmitting(false);
    });

    return () => cancelAnimationFrame(frameId);
  }, [location.pathname]);

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
      navigate("/result");
    } catch (error) {
      setSubmitError(error.message);
      setSubmitting(false);
    }
  }

  async function createRelatedPersonFromSubmissionPayload(payload) {
    const firstName = payload.payload_json.minor_first_name?.trim();
    const lastName = payload.payload_json.minor_last_name?.trim();
    const guardianRelation = payload.payload_json.guardian_relation?.trim();

    if (!firstName || !lastName || !guardianRelation) {
      throw new Error("Uzupełnij imię, nazwisko i typ opiekuna dla każdego podopiecznego.");
    }

    return createRelatedPerson({
      first_name: firstName,
      last_name: lastName,
      birth_date: null,
      guardian_relation: guardianRelation,
      image_publication_consent: Boolean(payload.consents_json.image_publication),
      vehicle_type: payload.vehicle_type,
      vehicle_brand: payload.payload_json.vehicle_brand || null,
      vehicle_model: payload.payload_json.vehicle_model || null,
      vehicle_registration_number:
        payload.payload_json.vehicle_registration_number || null,
    });
  }

  async function handleAccountSubmit(payloadOrArray) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      let results;
      const payloads = Array.isArray(payloadOrArray) ? payloadOrArray : [payloadOrArray];

      if (payloads[0]?.participant_role === "legal_guardian") {
        setSelectedRole("legal_guardian");
        setSelectedVehicle(payloads[0]?.vehicle_type || selectedVehicle || "car");
        results = [];
        for (const payload of payloads) {
          const { related_person_id: relatedPersonId, ...submissionPayload } = payload;
          const relatedPerson = relatedPersonId
            ? { id: relatedPersonId }
            : await createRelatedPersonFromSubmissionPayload(payload);
          results.push(
            await createSubmissionForRelatedPerson(
              relatedPerson.id,
              submissionPayload,
            ),
          );
        }
      } else {
        setSelectedRole(payloads[0]?.participant_role || null);
        setSelectedVehicle(payloads[0]?.vehicle_type || null);
        results = [await createAccountSubmission(payloads[0])];
      }
      if (refreshProfile) {
        await refreshProfile();
      }
      setSubmissionIsAccount(true);
      setSubmissions(results);
      navigate("/result");
    } catch (error) {
      setSubmitError(error.message);
      setSubmitting(false);
    }
  }

  function handleGuestNewSubmission() {
    setSubmissions(null);
    setSubmitError(null);
    navigate("/");
  }

  function handleAccountNewForm() {
    setSubmissions(null);
    setSubmitError(null);
    navigate("/account/verify");
  }

  function handleNextDependent() {
    setSubmissions(null);
    setSubmitError(null);
    setSelectedRole("legal_guardian");
    setSelectedVehicle(submissions?.[0]?.vehicle_type || selectedVehicle || "car");
    navigate("/account/verify");
  }

  if (isInitializing) {
    return (
      <div className="app-loader-screen">
        <div className="app-loader-spinner"></div>
        <p>Odtwarzanie sesji...</p>
      </div>
    );
  }
  if (loading) {
    return <p className="status-card">Ładowanie formularza...</p>;
  }
  if (loadError) {
    return (
      <div className="status-card alert" role="alert">
        <p>Nie udało się pobrać formularza: {loadError}</p>
        <p>Sprawdź, czy backend działa i czy proxy poprawnie wstrzykuje X-Kiosk-Token.</p>
      </div>
    );
  }

  return (
    <>
      {submitting && (
        <div className="app-loader-overlay" role="status" aria-live="polite" aria-busy="true">
          <div className="app-loader-spinner" aria-hidden="true"></div>
          <p>Wysyłanie formularza...</p>
        </div>
      )}
      {isAuthenticated && (
        <div className="app-container">
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
              Zalogowano jako: <strong>{user?.email}</strong>
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
        </div>
      )}
      <Routes>
        <Route
          path="/"
          element={
            <GuestOnlyRoute>
              <StartScreen
                infoMessage={startInfoMessage}
                onGuest={() => navigate("/guest")}
                onLogin={() => navigate("/login")}
                onRegister={() => navigate("/register")}
              />
            </GuestOnlyRoute>
          }
        />
        <Route
          path="/login"
          element={
            <GuestOnlyRoute>
              <LoginPage
                onBack={() => navigate("/")}
                onSuccess={(profile) =>
                  navigate(profile?.is_superuser ? "/admin" : "/account/verify", { replace: true })
                }
              />
            </GuestOnlyRoute>
          }
        />
        <Route
          path="/register"
          element={
            <GuestOnlyRoute>
              <RegisterPage onBack={() => navigate("/")} onSuccess={() => navigate("/account/verify")} />
            </GuestOnlyRoute>
          }
        />
        <Route
          path="/guest"
          element={
            <GuestOnlyRoute>
              <div className="app-container">
                <div style={{ marginBottom: "15px" }}>
                  <button
                    className="secondary-button"
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      navigate("/");
                    }}
                    onClick={() => navigate("/")}
                  >
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
            </GuestOnlyRoute>
          }
        />
        <Route
          path="/account/role"
          element={<Navigate to="/account/verify" replace />}
        />
        <Route
          path="/account/verify"
          element={
            <ProtectedRoute>
              <div className="app-container">
                  <GuestRegistrationForm
                    form={form}
                    mode="account"
                    role={selectedRole || ""}
                    vehicleType={selectedVehicle || ""}
                    onSubmit={handleAccountSubmit}
                    submitting={submitting}
                    submitError={submitError}
                    onRoleChange={setSelectedRole}
                    onVehicleTypeChange={setSelectedVehicle}
                  />
                </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <AdminOnlyRoute>
              <AdminHome />
            </AdminOnlyRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <AdminOnlyRoute>
              <AdminUsersPage />
            </AdminOnlyRoute>
          }
        />
        <Route
          path="/admin/submissions"
          element={
            <AdminOnlyRoute>
              <AdminSubmissionsPage />
            </AdminOnlyRoute>
          }
        />
        <Route
          path="/admin/submissions/:submissionId"
          element={
            <AdminOnlyRoute>
              <AdminSubmissionDetailsPage />
            </AdminOnlyRoute>
          }
        />
        <Route
          path="/result"
          element={
            submissions ? (
              <SubmissionResult
                submissions={submissions}
                isAccountMode={submissionIsAccount}
                onNewSubmission={handleGuestNewSubmission}
                onNewForm={handleAccountNewForm}
                onLogout={handleLogout}
                onNextDependent={
                  submissions.some(
                    (submission) => submission.participant_role === "legal_guardian",
                  )
                    ? handleNextDependent
                    : undefined
                }
              />
            ) : (
              <Navigate to={isAuthenticated ? defaultAuthenticatedRoute : "/"} replace />
            )
          }
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? defaultAuthenticatedRoute : "/"} replace />} />
      </Routes>
    </>
  );
}
