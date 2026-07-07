import { useCallback, useEffect, useState } from "react";

import { getFormPrefill } from "../api/auth.js";
import { FORM_SUBTITLE } from "../content/participantDeclarations.js";
import {
  IDENTITY_DOCUMENT_TYPES,
  PERSONAL_DATA_FIELDS,
  SIGNATURE_PLACE_FIELD,
  VEHICLE_DATA_FIELDS,
  buildPayloadJson,
  buildSubmissionPayload,
  getRoleLabel,
  getVehicleLabel,
  inferIdentityDocumentType,
  mapPrefillToFormData,
  validateForm,
} from "../lib/registrationFormShared.js";
import DeclarationsPanel from "../components/DeclarationsPanel.jsx";
import RadioGroup from "../components/RadioGroup.jsx";
import { renderFields } from "../components/registrationFormFields.jsx";
import SignaturePad from "../components/SignaturePad.jsx";

export default function VerifyDataForm({
  form,
  role,
  vehicleType,
  token,
  onSubmit,
  onBack,
  submitting,
  submitError,
}) {
  const schema = form.schema_json || {};
  const properties = schema.properties || {};

  const [formData, setFormData] = useState({});
  const [identityDocumentType, setIdentityDocumentType] = useState("pesel");
  const [declarationsReviewed, setDeclarationsReviewed] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [signatureImageBase64, setSignatureImageBase64] = useState(null);
  const [loadingPrefill, setLoadingPrefill] = useState(true);
  const [prefillError, setPrefillError] = useState(null);

  const loadPrefill = useCallback(async () => {
    setLoadingPrefill(true);
    setPrefillError(null);
    try {
      const prefill = await getFormPrefill(token, role, vehicleType);
      const mapped = mapPrefillToFormData(prefill);
      setFormData(mapped);
      setIdentityDocumentType(inferIdentityDocumentType(mapped));
    } catch (error) {
      setPrefillError(error.message || "Nie udało się pobrać danych profilu.");
    } finally {
      setLoadingPrefill(false);
    }
  }, [token, role, vehicleType]);

  useEffect(() => {
    loadPrefill();
  }, [loadPrefill]);

  function updateField(fieldName, value) {
    setFormData((current) => ({ ...current, [fieldName]: value }));
  }

  function handleIdentityDocumentTypeChange(value) {
    setIdentityDocumentType(value);
    setFormData((current) => {
      const next = { ...current };
      if (value === "pesel") {
        delete next.id_card_series;
        delete next.id_card_number;
      } else {
        delete next.pesel;
      }
      return next;
    });
  }

  function handleSubmit(event) {
    event.preventDefault();

    const basePayload = buildPayloadJson(formData, schema, identityDocumentType);
    const errors = validateForm({
      schema,
      payload: basePayload,
      participantRole: role,
      vehicleType,
      declarationsReviewed,
      identityDocumentType,
      signatureImageBase64,
      requireRoleSelection: false,
    });

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors([]);
    onSubmit(
      buildSubmissionPayload({
        basePayload,
        participantRole: role,
        vehicleType,
        signatureImageBase64,
      }),
    );
  }

  if (loadingPrefill) {
    return <p className="status-card">Ładowanie danych profilu...</p>;
  }

  if (prefillError) {
    return (
      <div className="status-card alert" role="alert">
        <p>Nie udało się pobrać danych: {prefillError}</p>
        <div className="actions">
          <button className="secondary-button" type="button" onClick={onBack}>
            &larr; Wróć
          </button>
          <button className="primary-button" type="button" onClick={loadPrefill}>
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="guest-form" onSubmit={handleSubmit}>
      <header className="form-header">
        <p className="eyebrow">Konto użytkownika</p>
        <h1>Weryfikacja danych – Autodrom Biłgoraj</h1>
        <p>{FORM_SUBTITLE}</p>
        <p className="hint">Wersja formularza: {form.version}</p>
      </header>

      <fieldset className="form-card">
        <legend>Wybrane opcje</legend>
        <p>
          <strong>Rola:</strong> {getRoleLabel(role)}
        </p>
        <p>
          <strong>Pojazd:</strong> {getVehicleLabel(vehicleType)}
        </p>
        <button className="secondary-button" type="button" onClick={onBack}>
          Zmień rolę lub pojazd
        </button>
      </fieldset>

      <fieldset className="form-card">
        <legend>Dane uczestnika</legend>
        <p className="hint">Sprawdź i popraw dane przed wysłaniem formularza.</p>
        {renderFields(PERSONAL_DATA_FIELDS, properties, schema, formData, updateField)}
        <div className="identity-fields">
          <RadioGroup
            legend="Dokument tożsamości"
            name="identity_document_type"
            options={IDENTITY_DOCUMENT_TYPES}
            value={identityDocumentType}
            onChange={handleIdentityDocumentTypeChange}
          />
          {identityDocumentType === "pesel" ? (
            <label className="field">
              <span>{properties.pesel?.title || "PESEL"}</span>
              <input
                type="text"
                inputMode="numeric"
                value={formData.pesel || ""}
                onChange={(event) => updateField("pesel", event.target.value)}
                pattern={properties.pesel?.pattern}
                maxLength={11}
                required
              />
            </label>
          ) : (
            <div className="field-row">
              <label className="field">
                <span>{properties.id_card_series?.title || "Seria dowodu osobistego"}</span>
                <input
                  type="text"
                  value={formData.id_card_series || ""}
                  onChange={(event) => updateField("id_card_series", event.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>{properties.id_card_number?.title || "Numer dowodu osobistego"}</span>
                <input
                  type="text"
                  value={formData.id_card_number || ""}
                  onChange={(event) => updateField("id_card_number", event.target.value)}
                  required
                />
              </label>
            </div>
          )}
        </div>
      </fieldset>

      <fieldset className="form-card">
        <legend>Dane pojazdu</legend>
        <p className="hint">Pola opcjonalne — wypełnij, jeśli dotyczy.</p>
        {renderFields(VEHICLE_DATA_FIELDS, properties, schema, formData, updateField, {
          forceOptional: true,
        })}
      </fieldset>

      <fieldset className="form-card">
        <legend>Oświadczenia oraz akceptacja ryzyka</legend>
        <p className="hint">Zapoznaj się z pełną treścią poniżej. Przewiń tekst do końca przed wysłaniem.</p>
        <DeclarationsPanel reviewed={declarationsReviewed} onReviewed={() => setDeclarationsReviewed(true)} />
        {!declarationsReviewed && (
          <p className="review-hint">Przewiń oświadczenia do końca, aby wysłać formularz.</p>
        )}
      </fieldset>

      <fieldset className="form-card">
        <legend>Data i miejscowość oraz podpis</legend>
        <div className="signature-section">
          <label className="field signature-place-field">
            <span>{properties.signature_place?.title || "Data i miejscowość"}</span>
            <input
              type="text"
              value={formData.signature_place || ""}
              onChange={(event) => updateField(SIGNATURE_PLACE_FIELD, event.target.value)}
              placeholder="np. Biłgoraj, 03.07.2026"
              required
            />
          </label>
          <div className="signature-pad-field">
            <p className="signature-footer-label">Czytelny podpis uczestnika</p>
            <SignaturePad onChange={setSignatureImageBase64} disabled={submitting} />
          </div>
        </div>
      </fieldset>

      {validationErrors.length > 0 && (
        <div className="alert" role="alert">
          <p>Błędy walidacji:</p>
          <ul>
            {validationErrors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {submitError && (
        <div className="alert" role="alert">
          <p>Błąd wysyłki: {submitError}</p>
        </div>
      )}

      <div className="actions">
        <button className="secondary-button" type="button" onClick={onBack} disabled={submitting}>
          &larr; Wróć
        </button>
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "Wysyłanie..." : "Wyślij"}
        </button>
      </div>
    </form>
  );
}
