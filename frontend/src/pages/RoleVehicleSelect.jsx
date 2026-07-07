import { useState } from "react";

import { PARTICIPANT_ROLES, VEHICLE_TYPES } from "../lib/registrationFormShared.js";
import RadioGroup from "../components/RadioGroup.jsx";

export default function RoleVehicleSelect({ onContinue, onBack }) {
  const [role, setRole] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [error, setError] = useState("");

  function handleNext() {
    if (!role) {
      setError("Proszę wybrać rolę uczestnika.");
      return;
    }
    if (!vehicle) {
      setError("Proszę wybrać rodzaj pojazdu.");
      return;
    }

    setError("");
    onContinue({ role, vehicle });
  }

  return (
    <div className="guest-form">
      <header className="form-header">
        <p className="eyebrow">Konto użytkownika</p>
        <h1>Wybierz rolę i pojazd</h1>
        <p className="hint">Określ, w jakiej roli bierzesz udział w jazdach.</p>
      </header>

      <fieldset className="form-card">
        <legend>Rola uczestnika</legend>
        <RadioGroup
          legend="Rola"
          name="participant_role"
          options={PARTICIPANT_ROLES}
          value={role}
          onChange={setRole}
          required={false}
        />
      </fieldset>

      <fieldset className="form-card">
        <legend>Rodzaj pojazdu</legend>
        <RadioGroup
          legend="Pojazd"
          name="vehicle_type"
          options={VEHICLE_TYPES}
          value={vehicle}
          onChange={setVehicle}
          required={false}
        />
      </fieldset>

      {error && (
        <div className="alert" role="alert">
          <p>{error}</p>
        </div>
      )}

      <div className="actions">
        {onBack && (
          <button className="secondary-button" type="button" onClick={onBack}>
            &larr; Wróć
          </button>
        )}
        <button className="primary-button" type="button" onClick={handleNext}>
          Dalej
        </button>
      </div>
    </div>
  );
}
