import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAdminSubmissionDetails, queueSubmissionForPrint } from "../../api/admin.js";
import { useAuth } from "../../context/AuthContext.jsx";
import AdminLayout from "./AdminLayout.jsx";

function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function AdminSubmissionDetailsPage() {
  const { token } = useAuth();
  const { submissionId } = useParams();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);
  const [acting, setActing] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminSubmissionDetails({ token, submissionId });
      setData(result);
    } catch (e) {
      setError(e.message || "Nie udało się pobrać szczegółów zgłoszenia.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submissionId]);

  async function handleQueuePrint() {
    setActionMessage(null);
    setActing(true);
    try {
      const result = await queueSubmissionForPrint({ token, submissionId });
      setActionMessage(result?.message || "Dodano do kolejki wydruku.");
      await load();
    } catch (e) {
      setError(e.message || "Nie udało się dodać do kolejki wydruku.");
    } finally {
      setActing(false);
    }
  }

  return (
    <AdminLayout
      title="Szczegóły zgłoszenia"
      subtitle="Podgląd danych formularza i akcje związane z drukiem."
      activeHref="/admin/submissions"
    >
      <div className="form-card">
        <div className="minor-table-header">
          <h3 className="admin-mono" style={{ margin: 0 }}>
            #{String(submissionId).slice(0, 8)}
          </h3>
          <div className="actions" style={{ margin: 0 }}>
            <Link className="secondary-button" to="/admin/submissions">
              &larr; Powrót
            </Link>
            <button type="button" className="primary-button" disabled={acting} onClick={handleQueuePrint}>
              {acting ? "Dodawanie…" : "Dodaj do druku"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="status-card alert" role="alert">
          {error}
        </div>
      )}
      {actionMessage && (
        <div className="status-card" role="status">
          {actionMessage}
        </div>
      )}

      {loading ? (
        <p className="status-card">Ładowanie…</p>
      ) : data ? (
        <>
          <div className="form-card">
            <div className="field-row">
              <div className="field">
                <span>Status</span>
                <div className="hint">{data.status}</div>
              </div>
            </div>

            <div className="field-row">
              <div className="field">
                <span>Data (sequence)</span>
                <div className="hint">{String(data.sequence_date || "-")}</div>
              </div>
              <div className="field">
                <span>Start nr.</span>
                <div className="hint">{String(data.start_number)}</div>
              </div>
            </div>
          </div>

          <div className="form-card">
            <details open>
              <summary style={{ fontWeight: 800, marginBottom: 10 }}>Dane formularza</summary>
              <pre className="admin-json" style={{ margin: 0, maxHeight: 380 }}>
                {prettyJson(data.payload_json)}
              </pre>
            </details>
          </div>

          <div className="form-card">
            <details>
              <summary style={{ fontWeight: 800, marginBottom: 10 }}>Zgody</summary>
              <pre className="admin-json" style={{ margin: 0, maxHeight: 320 }}>
                {prettyJson(data.consents_json)}
              </pre>
            </details>
          </div>
        </>
      ) : (
        <p className="status-card">Brak danych.</p>
      )}
    </AdminLayout>
  );
}

