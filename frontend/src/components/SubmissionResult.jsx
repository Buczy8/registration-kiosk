import { useEffect, useRef, useState } from "react";

import { fetchSubmissionPdfBlob } from "../api/kiosk.js";

export default function SubmissionResult({ submissions, onNewSubmission }) {
  const isMultiple = submissions.length > 1;
  const [activeSubmissionId, setActiveSubmissionId] = useState(submissions[0]?.id ?? null);
  const [pdfUrls, setPdfUrls] = useState({});
  const [loadingPreview, setLoadingPreview] = useState(true);
  const [previewError, setPreviewError] = useState(null);
  const objectUrlsRef = useRef([]);

  useEffect(() => {
    let cancelled = false;
    const createdUrls = [];

    async function loadPreviews() {
      setLoadingPreview(true);
      setPreviewError(null);
      setPdfUrls({});

      try {
        const nextUrls = {};
        for (const submission of submissions) {
          const blob = await fetchSubmissionPdfBlob(submission.id);
          if (cancelled) {
            return;
          }
          const url = URL.createObjectURL(blob);
          createdUrls.push(url);
          nextUrls[submission.id] = url;
        }
        objectUrlsRef.current = createdUrls;
        if (!cancelled) {
          setPdfUrls(nextUrls);
        }
      } catch (error) {
        createdUrls.forEach((url) => URL.revokeObjectURL(url));
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
      createdUrls.forEach((url) => URL.revokeObjectURL(url));
      objectUrlsRef.current = [];
    };
  }, [submissions]);

  const activePdfUrl = activeSubmissionId ? pdfUrls[activeSubmissionId] : null;

  return (
    <section className="result-card">
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
            {isMultiple && (
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

      <div className="pdf-preview-panel">
        <h2>Podgląd dokumentu</h2>
        {loadingPreview && <p>Ładowanie podglądu PDF...</p>}
        {previewError && (
          <p className="alert" role="alert">
            Nie udało się wyświetlić PDF: {previewError}
          </p>
        )}
        {!loadingPreview && !previewError && activePdfUrl && (
          <iframe
            className="pdf-preview-frame"
            src={activePdfUrl}
            title="Podgląd zgłoszenia PDF"
          />
        )}
      </div>

      <div className="actions">
        <button className="primary-button" type="button" onClick={onNewSubmission}>
          Nowa rejestracja
        </button>
      </div>
    </section>
  );
}
