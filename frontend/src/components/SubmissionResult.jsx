export default function SubmissionResult({
  submissions,
  onDownloadPdf,
  downloadingId,
  downloadErrors,
  onNewSubmission,
}) {
  const isMultiple = submissions.length > 1;

  return (
    <section className="result-card">
      <h1>Rejestracja zakończona</h1>
      {isMultiple ? (
        <p>Utworzono {submissions.length} zgłoszenia. Każde ma osobny numer startowy i PDF.</p>
      ) : (
        <p>Numer startowy</p>
      )}

      <ul className="submission-results">
        {submissions.map((submission) => (
          <li className="submission-result-item" key={submission.id}>
            <p className="result-number">{submission.start_number}</p>
            <p>Data sekwencji: {submission.sequence_date}</p>
            <p>Status: {submission.status}</p>
            <p>ID zgłoszenia: {submission.id}</p>
            <button
              className="primary-button"
              type="button"
              onClick={() => onDownloadPdf(submission.id)}
              disabled={downloadingId === submission.id}
            >
              {downloadingId === submission.id ? "Pobieranie PDF..." : "Pobierz PDF"}
            </button>
            {downloadErrors[submission.id] && (
              <p role="alert">Błąd pobierania PDF: {downloadErrors[submission.id]}</p>
            )}
          </li>
        ))}
      </ul>

      <div className="actions">
        <button className="secondary-button" type="button" onClick={onNewSubmission}>
          Nowa rejestracja
        </button>
      </div>
    </section>
  );
}
