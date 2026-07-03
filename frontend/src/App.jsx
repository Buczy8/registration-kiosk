import { useEffect, useState } from "react";
import { createGuestSubmission, getActiveForm } from "./api/kiosk.js";
import GuestRegistrationForm from "./components/GuestRegistrationForm.jsx";
import SubmissionResult from "./components/SubmissionResult.jsx";

export default function App() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [submissions, setSubmissions] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

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
        results.push(await createGuestSubmission(payload));
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

  return (
    <GuestRegistrationForm
      form={form}
      onSubmit={handleSubmit}
      submitting={submitting}
      submitError={submitError}
    />
  );
}
