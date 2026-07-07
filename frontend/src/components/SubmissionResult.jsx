import { useEffect, useState } from "react";

import { fetchSubmissionPdfBlob } from "../api/kiosk.js";
import PdfPreview from "./PdfPreview.jsx";

export default function SubmissionResult({
  submissions,
  onNewSubmission,
  isAccountMode = false,
  onLogout,
  onNewForm,
}) {
  const isMultiple = submissions.length > 1;
  const [activeSubmissionId, setActiveSubmissionId] = useState(submissions[0]?.id ?? null);
  const [pdfBlobs, setPdfBlobs] = useState({});
  const [loadingPreview, setLoadingPreview] = useState(!isAccountMode);
  const [previewError, setPreviewError] = useState(null);

  useEffect(() => {
    if (isAccountMode) {
      return undefined;
    }

    let cancelled = false;

    async function loadPreviews() {
      setLoadingPreview(true);
      setPreviewError(null);
      setPdfBlobs({});

      try {
        const nextBlobs = {};
        for (const submission of submissions) {
          const blob = await fetchSubmissionPdfBlob(submission.id);
          if (cancelled) {
            return;
          }
          nextBlobs[submission.id] = blob;
        }
        if (!cancelled) {
          setPdfBlobs(nextBlobs);
        }
      } catch (error) {
        if (!cancelled) {
          setPreviewError(error.message);
        }
      } finally {
        if (!cancelled) {
          setLoadingPreview(false);
        }
      }
    }

    loadPreviews();

    return () => {
      cancelled = true;
    };
  }, [submissions, isAccountMode]);

  const activePdfBlob = activeSubmissionId ? pdfBlobs[activeSubmissionId] : null;

  return (
    <section className="result-card result-screen">
      <h1>Rejestracja zakończona</h1>
      {isMultiple ? (
        <p>Utworzono {submissions.length} zgłoszenia. Podgląd dokumentu dla każdego podopiecznego.</p>
      ) : (
        <p>Numer startowy</p>
      )}

      <ul className="submission-results">
        {submissions.map((submission) => (
          <li className="submission-result-item" key={submission.id}>
            <p className="result-number">{submission.start_number}</p>
            <p>Data sekwencji: {submission.sequence_date}</p>
            <p>Status: {submission.status}</p>
            {isMultiple && !isAccountMode && (
              <button
                className={
                  activeSubmissionId === submission.id ? "primary-button" : "secondary-button"
                }
                type="button"
                onClick={() => setActiveSubmissionId(submission.id)}
              >
                Podgląd PDF
              </button>
            )}
          </li>
        ))}
      </ul>

      {!isAccountMode && (
        <div className="pdf-preview-panel">
          <h2>Podgląd dokumentu</h2>
          {loadingPreview && <p>Ładowanie podglądu PDF...</p>}
          {previewError && (
            <p className="alert" role="alert">
              Nie udało się wyświetlić PDF: {previewError}
            </p>
          )}
          {!loadingPreview && !previewError && activePdfBlob && (
            <PdfPreview blob={activePdfBlob} title="Podgląd zgłoszenia PDF" />
          )}
        </div>
      )}

      <div className="actions">
        {isAccountMode ? (
          <>
            {onNewForm && (
              <button className="primary-button" type="button" onClick={onNewForm}>
                Nowy formularz
              </button>
            )}
            {onLogout && (
              <button className="secondary-button" type="button" onClick={onLogout}>
                Wyloguj
              </button>
            )}
          </>
        ) : (
          <button className="primary-button" type="button" onClick={onNewSubmission}>
            Nowa rejestracja
          </button>
        )}
      </div>
    </section>
  );
}
