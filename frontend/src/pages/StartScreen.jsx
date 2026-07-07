import React from "react";

export default function StartScreen({ onGuest, onLogin, onRegister }) {
  return (
    <div className="start-screen">
      <div className="start-card">
        <h1>Witamy w systemie rejestracji</h1>
        <p>Wybierz sposób, w jaki chcesz kontynuować:</p>

        <div className="start-actions">
          <button
            className="primary-button touch-button"
            onClick={onGuest}
          >
            Gość
          </button>

          <button
            className="secondary-button touch-button"
            onClick={onLogin}
          >
            Zaloguj
          </button>

          <button
            className="secondary-button touch-button"
            onClick={onRegister}
          >
            Zarejestruj
          </button>
        </div>
      </div>
    </div>
  );
}