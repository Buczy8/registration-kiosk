export default function GuardianPlaceholder({ onBack }) {
  return (
    <section className="status-card">
      <h1>Rejestracja podopiecznych</h1>
      <p>Funkcja rejestracji podopiecznych będzie dostępna wkrótce.</p>
      <p className="hint">W tej wersji aplikacji możesz zarejestrować się jako kierowca lub pasażer.</p>
      <div className="actions">
        <button className="primary-button" type="button" onClick={onBack}>
          &larr; Wróć do wyboru roli
        </button>
      </div>
    </section>
  );
}
