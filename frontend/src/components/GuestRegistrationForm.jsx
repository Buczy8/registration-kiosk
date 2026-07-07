import { useState } from "react";

import {
  FORM_SUBTITLE,
  GUARDIAN_DECLARATION_INTRO,
  IMAGE_PUBLICATION_CONSENT_TEXT,
} from "../content/participantDeclarations.js";
import {
  GUARDIAN_FIELDS,
  GUARDIAN_RELATIONS,
  IDENTITY_DOCUMENT_TYPES,
  PARTICIPANT_ROLES,
  PERSONAL_DATA_FIELDS,
  SIGNATURE_PLACE_FIELD,
  VEHICLE_DATA_FIELDS,
  VEHICLE_TYPES,
  buildPayloadJson,
  buildSubmissionPayload,
  createEmptyMinor,
  getDefaultSignaturePlace,
  validateForm,
} from "../lib/registrationFormShared.js";
import DeclarationsPanel from "./DeclarationsPanel.jsx";
import RadioGroup from "./RadioGroup.jsx";
import { renderFields, renderMinorVehicleFields } from "./registrationFormFields.jsx";
import SignaturePad from "./SignaturePad.jsx";

export default function GuestRegistrationForm({ form, onSubmit, submitting, submitError }) {
  const schema = form.schema_json || {};
  const properties = schema.properties || {};

  const [participantRole, setParticipantRole] = useState("driver");
  const [vehicleType, setVehicleType] = useState("car");
  const [identityDocumentType, setIdentityDocumentType] = useState("pesel");
  const [formData, setFormData] = useState({
    [SIGNATURE_PLACE_FIELD]: getDefaultSignaturePlace(),
  });
  const [minors, setMinors] = useState([createEmptyMinor()]);
  const [consents, setConsents] = useState({ image_publication: false });
  const [declarationsReviewed, setDeclarationsReviewed] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [signatureImageBase64, setSignatureImageBase64] = useState(null);

  function updateField(fieldName, value) {
    setFormData((current) => ({ ...current, [fieldName]: value }));
  }

  function updateMinor(minorId, fieldName, value) {
    setMinors((current) =>
      current.map((minor) => (minor.id === minorId ? { ...minor, [fieldName]: value } : minor)),
    );
  }

  function addMinor() {
    setMinors((current) => [...current, createEmptyMinor()]);
  }

  function removeMinor(minorId) {
    setMinors((current) => {
      if (current.length === 1) {
        return current;
      }
      return current.filter((minor) => minor.id !== minorId);
    });
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

  function handleParticipantRoleChange(value) {
    setParticipantRole(value);
    if (value === "legal_guardian") {
      setMinors([createEmptyMinor()]);
      return;
    }

    setMinors([createEmptyMinor()]);
    setFormData((current) => {
      const next = { ...current };
      for (const fieldName of GUARDIAN_FIELDS) {
        delete next[fieldName];
      }
      return next;
    });
  }

  function handleSubmit(event) {
    event.preventDefault();

    const basePayload = buildPayloadJson(formData, schema, identityDocumentType, {
      excludeVehicleFields: participantRole === "legal_guardian",
    });
    const errors = validateForm({
      schema,
      payload: basePayload,
      participantRole,
      vehicleType,
      declarationsReviewed,
      identityDocumentType,
      minors,
      signatureImageBase64,
    });

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors([]);

    if (participantRole === "legal_guardian") {
      onSubmit(
        minors.map((minor) =>
          buildSubmissionPayload({
            basePayload,
            minor,
            participantRole,
            vehicleType,
            consents,
            signatureImageBase64,
          }),
        ),
      );
      return;
    }

    onSubmit(
      buildSubmissionPayload({
        basePayload,
        participantRole,
        vehicleType,
        consents,
        signatureImageBase64,
      }),
    );
  }

  return (
    <form className="guest-form" onSubmit={handleSubmit}>
      <header className="form-header">
        <p className="eyebrow">Kiosk gościa</p>
        <h1>Oświadczenie uczestnika – Autodrom Biłgoraj</h1>
        <p>{FORM_SUBTITLE}</p>
        <p className="hint">Wersja formularza: {form.version}</p>
      </header>

      <fieldset className="form-card">
        <legend>I. Status uczestnika oraz rodzaj jazd</legend>
        <RadioGroup
          legend="Rola"
          name="participant_role"
          options={PARTICIPANT_ROLES}
          value={participantRole}
          onChange={handleParticipantRoleChange}
        />
        {participantRole !== "legal_guardian" && (
          <RadioGroup
            legend="Rodzaj pojazdu"
            name="vehicle_type"
            options={VEHICLE_TYPES}
            value={vehicleType}
            onChange={setVehicleType}
          />
        )}
      </fieldset>

      <fieldset className="form-card">
        <legend>
          II. Dane {participantRole === "legal_guardian" ? "opiekuna" : "uczestnika"}
        </legend>
        {participantRole === "legal_guardian" && (
          <p className="hint">Wypełnij swoje dane jako opiekun prawny.</p>
        )}
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

      {participantRole !== "legal_guardian" && (
        <fieldset className="form-card">
          <legend>III. Dane pojazdu</legend>
          <p className="hint">Pola opcjonalne — wypełnij, jeśli dotyczy.</p>
          {renderFields(VEHICLE_DATA_FIELDS, properties, schema, formData, updateField, {
            forceOptional: true,
          })}
        </fieldset>
      )}

      <fieldset className="form-card">
        <legend>IV. Oświadczenia oraz akceptacja ryzyka</legend>
        <p className="hint">Zapoznaj się z pełną treścią poniżej. Przewiń tekst do końca przed wysłaniem.</p>
        <DeclarationsPanel reviewed={declarationsReviewed} onReviewed={() => setDeclarationsReviewed(true)} />
        {!declarationsReviewed && (
          <p className="review-hint">Przewiń oświadczenia do końca, aby wysłać formularz.</p>
        )}
      </fieldset>

      {participantRole === "legal_guardian" && (
        <fieldset className="form-card">
          <legend>V. Dla opiekunów prawnych (osoby niepełnoletnie)</legend>
          <p className="guardian-declaration">{GUARDIAN_DECLARATION_INTRO}</p>
          <p className="hint">
            Dodaj jednego lub więcej podopiecznych. Dla każdego zostanie utworzone osobne zgłoszenie i PDF.
          </p>
          {minors.map((minor, index) => (
            <div className="minor-card" key={minor.id}>
              <div className="minor-card-header">
                <h3>Podopieczny {index + 1}</h3>
                {minors.length > 1 && (
                  <button
                    className="secondary-button minor-remove-button"
                    type="button"
                    onClick={() => removeMinor(minor.id)}
                  >
                    Usuń
                  </button>
                )}
              </div>
              <RadioGroup
                legend="Typ opiekuna"
                name={`guardian_relation_${minor.id}`}
                options={GUARDIAN_RELATIONS}
                value={minor.guardian_relation}
                onChange={(value) => updateMinor(minor.id, "guardian_relation", value)}
              />
              <div className="field-row">
                <label className="field">
                  <span>Imię podopiecznego</span>
                  <input
                    type="text"
                    value={minor.minor_first_name}
                    onChange={(event) =>
                      updateMinor(minor.id, "minor_first_name", event.target.value)
                    }
                    required
                  />
                </label>
                <label className="field">
                  <span>Nazwisko podopiecznego</span>
                  <input
                    type="text"
                    value={minor.minor_last_name}
                    onChange={(event) =>
                      updateMinor(minor.id, "minor_last_name", event.target.value)
                    }
                    required
                  />
                </label>
              </div>
              {renderMinorVehicleFields(minor, properties, updateMinor)}
            </div>
          ))}
          <button className="secondary-button" type="button" onClick={addMinor}>
            Dodaj podopiecznego
          </button>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={consents.image_publication}
              onChange={(event) =>
                setConsents((current) => ({
                  ...current,
                  image_publication: event.target.checked,
                }))
              }
            />
            <span>{IMAGE_PUBLICATION_CONSENT_TEXT}</span>
          </label>
        </fieldset>
      )}

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
            <p className="signature-footer-label">Czytelny podpis uczestnika / opiekuna</p>
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

      <button className="primary-button" type="submit" disabled={submitting}>
        {submitting ? "Wysyłanie..." : "Wyślij"}
      </button>
    </form>
  );
}
