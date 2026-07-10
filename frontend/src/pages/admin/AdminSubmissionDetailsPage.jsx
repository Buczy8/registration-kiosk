import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchAdminSubmissionPdf,
  getAdminSubmissionDetails,
  queueSubmissionForPrint,
} from "../../api/admin.js";
import PdfPreview from "../../components/PdfPreview.jsx";
import { downloadPdfBlob } from "../../lib/adminPrint.js";
import AdminLayout from "./AdminLayout.jsx";

function submissionPdfFilename(data, submissionId) {
  return `wydruk_zgloszenia_${data?.start_number || submissionId}.pdf`;
}

export default function AdminSubmissionDetailsPage() {
  const { submissionId } = useParams();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);
  const [acting, setActing] = useState(false);

  const [pdfBlob, setPdfBlob] = useState(null);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState(null);

  async function loadPdfPreview() {
    setLoadingPdf(true);
    setPdfError(null);
    try {
      const blob = await fetchAdminSubmissionPdf({ submissionId });
      setPdfBlob(blob);
      return blob;
    } catch (e) {
      setPdfError(e.message || "Nie udało się pobrać podglądu PDF.");
      setPdfBlob(null);
      return null;
    } finally {
      setLoadingPdf(false);
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminSubmissionDetails({ submissionId });
      setData(result);
      await loadPdfPreview();
    } catch (e) {
      setError(e.message || "Nie udało się pobrać szczegółów zgłoszenia.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setPdfBlob(null);
    setPdfError(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submissionId]);

  async function handleQueuePrint() {
    setActionMessage(null);
    setActing(true);
    try {
      await queueSubmissionForPrint({ submissionId });
      setActionMessage("Wydruk został wysłany.");
      await load();
    } catch (e) {
      setError(e.message || "Nie udało się wydrukować zgłoszenia.");
    } finally {
      setActing(false);
    }
  }

  function handleDownloadPdf() {
    if (!pdfBlob) return;
    setActionMessage(null);
    downloadPdfBlob(pdfBlob, submissionPdfFilename(data, submissionId));
    setActionMessage("Plik PDF pobrany.");
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
              {acting ? "Drukowanie…" : "Drukuj"}
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
      {pdfError && (
        <div className="status-card alert" role="alert">
          {pdfError}
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

          {loadingPdf ? (
            <p className="status-card">Ładowanie podglądu PDF…</p>
          ) : pdfBlob ? (
            <div className="form-card pdf-preview-panel">
              <div className="minor-table-header">
                <h3 style={{ margin: 0 }}>Podgląd PDF</h3>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleDownloadPdf}
                >
                  Pobierz plik
                </button>
              </div>
              <PdfPreview blob={pdfBlob} title="Podgląd zgłoszenia PDF" />
            </div>
          ) : null}

        </>
      ) : (
        <p className="status-card">Brak danych.</p>
      )}
    </AdminLayout>
  );
}
