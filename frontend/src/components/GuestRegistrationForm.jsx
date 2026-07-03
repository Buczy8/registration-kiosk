import { useState } from "react";

import { FORM_SUBTITLE } from "../content/participantDeclarations.js";
import DeclarationsPanel from "./DeclarationsPanel.jsx";

const PARTICIPANT_ROLES = [
  { value: "driver", label: "Kierowca" },
  { value: "passenger", label: "Pasażer" },
  { value: "legal_guardian", label: "Opiekun prawny" },
];

const VEHICLE_TYPES = [
  { value: "car", label: "Samochód" },
  { value: "motorcycle", label: "Motocykl" },
  { value: "gokart", label: "Gokart" },
];

const IDENTITY_DOCUMENT_TYPES = [
  { value: "pesel", label: "PESEL" },
  { value: "id_card", label: "Dowód osobisty (seria i numer)" },
];
const IDENTITY_FIELDS = ["pesel", "id_card_series", "id_card_number"];
const GUARDIAN_FIELDS = ["guardian_relation", "minor_first_name", "minor_last_name"];
const VEHICLE_DATA_FIELDS = [
  "vehicle_brand",
  "vehicle_model",
  "vehicle_registration_number",
];
const PERSONAL_DATA_FIELDS = [
  "first_name",
  "last_name",
  "residence_address",
  "birth_date",
  "phone",
  "email",
  "emergency_contact_name",
  "emergency_contact_phone",
];
const GUARDIAN_RELATIONS = [
  { value: "parent", label: "Rodzic" },
  { value: "guardian", label: "Opiekun prawny" },
  { value: "authorized_person", label: "Osoba upoważniona" },
];
const SIGNATURE_PLACE_FIELD = "signature_place";

function getDefaultSignaturePlace() {
  const today = new Date().toLocaleDateString("pl-PL");
  return `Biłgoraj, ${today}`;
}

function createEmptyMinor() {
  return {
    id: crypto.randomUUID(),
    guardian_relation: "",
    minor_first_name: "",
    minor_last_name: "",
    vehicle_type: "car",
    vehicle_brand: "",
    vehicle_model: "",
    vehicle_registration_number: "",
  };
}

function getInputType(property) {
  if (property.format === "date") {
    return "date";
  }
  if (property.format === "email") {
    return "email";
  }
  return "text";
}

function isIdentityField(fieldName) {
  return IDENTITY_FIELDS.includes(fieldName);
}

function isGuardianField(fieldName) {
  return GUARDIAN_FIELDS.includes(fieldName);
}

function isVehicleField(fieldName) {
  return VEHICLE_DATA_FIELDS.includes(fieldName);
}

function validateIdentityDocument(payload, schema, identityDocumentType) {
  if (schema.identity_document_rule !== "pesel_or_id_card") {
    return null;
  }

  if (identityDocumentType === "pesel") {
    if (!payload.pesel?.trim()) {
      return "Podaj PESEL.";
    }
    if (payload.pesel.trim().length !== 11) {
      return "PESEL musi mieć 11 cyfr.";
    }
    return null;
  }

  const hasSeries = Boolean(payload.id_card_series?.trim());
  const hasNumber = Boolean(payload.id_card_number?.trim());
  if (!hasSeries || !hasNumber) {
    return "Podaj serię i numer dowodu osobistego.";
  }

  return null;
}

function validateMinors(minors) {
  const errors = [];

  if (minors.length === 0) {
    errors.push("Dodaj co najmniej jednego podopiecznego.");
    return errors;
  }

  minors.forEach((minor, index) => {
    const label = `Podopieczny ${index + 1}`;
    if (!minor.guardian_relation?.trim()) {
      errors.push(`${label}: wybierz typ opiekuna.`);
    }
    if (!minor.minor_first_name?.trim()) {
      errors.push(`${label}: podaj imię podopiecznego.`);
    }
    if (!minor.minor_last_name?.trim()) {
      errors.push(`${label}: podaj nazwisko podopiecznego.`);
    }
  });

  return errors;
}

function validateForm({
  schema,
  payload,
  participantRole,
  vehicleType,
  consents,
  declarationsReviewed,
  identityDocumentType,
  minors,
}) {
  const errors = [];

  if (!participantRole) {
    errors.push("Wybierz rolę uczestnika.");
  }
  if (participantRole !== "legal_guardian" && !vehicleType) {
    errors.push("Wybierz typ pojazdu.");
  }

  for (const field of schema.required || []) {
    if (isGuardianField(field) || isVehicleField(field)) {
      continue;
    }
    if (!payload[field]?.trim()) {
      const title = schema.properties?.[field]?.title || field;
      errors.push(`Pole wymagane: ${title}.`);
    }
  }

  const identityError = validateIdentityDocument(payload, schema, identityDocumentType);
  if (identityError) {
    errors.push(identityError);
  }

  if (participantRole === "legal_guardian") {
    errors.push(...validateMinors(minors));
  }

  if (!declarationsReviewed) {
    errors.push("Przewiń i zapoznaj się z oświadczeniami oraz akceptacją ryzyka.");
  }
  if (!consents.privacy) {
    errors.push("Zaakceptuj zgodę na przetwarzanie danych osobowych.");
  }
  if (!payload[SIGNATURE_PLACE_FIELD]?.trim()) {
    errors.push("Podaj datę i miejscowość.");
  }

  return errors;
}

function buildPayloadJson(formData, schema, identityDocumentType, { excludeVehicleFields = false } = {}) {
  const payload = {};
  const properties = schema.properties || {};

  for (const fieldName of Object.keys(properties)) {
    if (isGuardianField(fieldName)) {
      continue;
    }
    if (excludeVehicleFields && isVehicleField(fieldName)) {
      continue;
    }
    if (isIdentityField(fieldName)) {
      if (identityDocumentType === "pesel" && fieldName !== "pesel") {
        continue;
      }
      if (identityDocumentType === "id_card" && fieldName === "pesel") {
        continue;
      }
    }
    const value = formData[fieldName]?.trim();
    if (value) {
      payload[fieldName] = value;
    }
  }

  if (!excludeVehicleFields) {
    applyVehicleFields(payload, formData);
  }

  payload[SIGNATURE_PLACE_FIELD] = formData[SIGNATURE_PLACE_FIELD]?.trim() || "";

  return payload;
}

function applyVehicleFields(payload, source) {
  for (const fieldName of VEHICLE_DATA_FIELDS) {
    payload[fieldName] = source[fieldName]?.trim() || "";
  }
  return payload;
}

function buildSubmissionPayload({
  basePayload,
  minor,
  participantRole,
  vehicleType,
  consents,
}) {
  const payloadJson = { ...basePayload };
  if (participantRole === "legal_guardian" && minor) {
    payloadJson.guardian_relation = minor.guardian_relation;
    payloadJson.minor_first_name = minor.minor_first_name.trim();
    payloadJson.minor_last_name = minor.minor_last_name.trim();
    applyVehicleFields(payloadJson, minor);
  }

  return {
    participant_role: participantRole,
    vehicle_type: minor?.vehicle_type ?? vehicleType,
    payload_json: payloadJson,
    consents_json: {
      privacy: true,
      image_publication: consents.image_publication,
    },
    declarations_accepted: true,
  };
}

function renderFields(fieldNames, properties, schema, formData, updateField, { forceOptional = false } = {}) {
  return fieldNames
    .filter((fieldName) => properties[fieldName])
    .map((fieldName) => {
      const property = properties[fieldName];
      const required =
        !forceOptional &&
        !isVehicleField(fieldName) &&
        (schema.required || []).includes(fieldName);
      return (
        <label className="field" key={fieldName}>
          <span>{property.title || fieldName}</span>
          <input
            type={getInputType(property)}
            value={formData[fieldName] || ""}
            onChange={(event) => updateField(fieldName, event.target.value)}
            pattern={property.pattern}
            required={required}
          />
        </label>
      );
    });
}

function renderMinorVehicleFields(minor, properties, updateMinor) {
  return (
    <div className="minor-vehicle-fields">
      <p className="identity-label">Dane pojazdu (opcjonalnie)</p>
      <RadioGroup
        legend="Rodzaj pojazdu"
        name={`vehicle_type_${minor.id}`}
        options={VEHICLE_TYPES}
        value={minor.vehicle_type}
        onChange={(value) => updateMinor(minor.id, "vehicle_type", value)}
      />
      <div className="field-row">
        <label className="field">
          <span>{properties.vehicle_brand?.title || "Marka pojazdu"}</span>
          <input
            type="text"
            value={minor.vehicle_brand}
            onChange={(event) => updateMinor(minor.id, "vehicle_brand", event.target.value)}
          />
        </label>
        <label className="field">
          <span>{properties.vehicle_model?.title || "Model pojazdu"}</span>
          <input
            type="text"
            value={minor.vehicle_model}
            onChange={(event) => updateMinor(minor.id, "vehicle_model", event.target.value)}
          />
        </label>
      </div>
      <label className="field">
        <span>{properties.vehicle_registration_number?.title || "Numer rejestracyjny"}</span>
        <input
          type="text"
          value={minor.vehicle_registration_number}
          onChange={(event) =>
            updateMinor(minor.id, "vehicle_registration_number", event.target.value)
          }
        />
      </label>
    </div>
  );
}

function RadioGroup({ legend, name, options, value, onChange, required = true }) {
  return (
    <fieldset className="radio-group">
      <legend>{legend}</legend>
      <div className="radio-options">
        {options.map((option) => (
          <label className="radio-option" key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(event) => onChange(event.target.value)}
              required={required}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

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
  const [consents, setConsents] = useState({ privacy: false, image_publication: false });
  const [declarationsReviewed, setDeclarationsReviewed] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);

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
      consents,
      declarationsReviewed,
      identityDocumentType,
      minors,
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
          <legend>V. Dla opiekunów prawnych</legend>
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
        </fieldset>
      )}

      <fieldset className="form-card">
        <legend>Zgody</legend>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={consents.privacy}
            onChange={(event) =>
              setConsents((current) => ({ ...current, privacy: event.target.checked }))
            }
            required
          />
          <span>
            Wyrażam zgodę na przetwarzanie danych osobowych w celu organizacji wydarzenia.{" "}
            <em>(zgoda obowiązkowa)</em>
          </span>
        </label>
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
          <span>
            Wyrażam zgodę na nieodpłatne utrwalanie i publikację mojego wizerunku oraz wizerunku
            mojego pojazdu w celach promocyjnych Autodromu Biłgoraj.
          </span>
        </label>
      </fieldset>

      <fieldset className="form-card">
        <legend>Data i miejscowość</legend>
        <label className="field">
          <span>{properties.signature_place?.title || "Data i miejscowość"}</span>
          <input
            type="text"
            value={formData.signature_place || ""}
            onChange={(event) => updateField(SIGNATURE_PLACE_FIELD, event.target.value)}
            placeholder="np. Biłgoraj, 03.07.2026"
            required
          />
        </label>
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
