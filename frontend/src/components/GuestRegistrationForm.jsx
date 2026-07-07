import { useMemo, useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  FORM_SUBTITLE,
  GUARDIAN_DECLARATION_INTRO,
  IMAGE_PUBLICATION_CONSENT_TEXT,
} from "../content/participantDeclarations.js";
import {
  GUARDIAN_FIELDS,
  GUARDIAN_RELATIONS,
  PARTICIPANT_ROLES,
  PERSONAL_DATA_FIELDS,
  SIGNATURE_PLACE_FIELD,
  VEHICLE_TYPES,
  buildPayloadJson,
  buildSubmissionPayload,
  createEmptyMinor,
  getDefaultSignaturePlace,
} from "../lib/registrationFormShared.js";
import { buildFormSchema, flattenZodErrors } from "../lib/registrationSchemas.js";
import DeclarationsPanel from "./DeclarationsPanel.jsx";
import FormValidationAlert from "./form/FormValidationAlert.jsx";
import IdentityDocumentSection from "./form/IdentityDocumentSection.jsx";
import PersonalDataSection from "./form/PersonalDataSection.jsx";
import SignatureSection from "./form/SignatureSection.jsx";
import VehicleDataSection from "./form/VehicleDataSection.jsx";
import RadioGroup from "./RadioGroup.jsx";
import { renderMinorVehicleFields } from "./registrationFormFields.jsx";

export default function GuestRegistrationForm({ form, onSubmit, submitting, submitError }) {
  const schema = useMemo(() => form.schema_json || {}, [form.schema_json]);
  const properties = schema.properties || {};
  const formSchema = useMemo(
    () => buildFormSchema({ schemaJson: schema, requireRoleSelection: true }),
    [schema],
  );

  const [validationErrors, setValidationErrors] = useState([]);

  const { control, handleSubmit, setValue, getValues } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      participantRole: "driver",
      vehicleType: "car",
      identityDocumentType: "pesel",
      payload: {
        [SIGNATURE_PLACE_FIELD]: getDefaultSignaturePlace(),
      },
      declarationsReviewed: false,
      signatureImageBase64: "",
      minors: [createEmptyMinor()],
      consents: { image_publication: false },
    },
  });

  const { fields: minors, append, remove, replace } = useFieldArray({ control, name: "minors" });

  const participantRole = useWatch({ control, name: "participantRole" }) || "driver";
  const vehicleType = useWatch({ control, name: "vehicleType" }) || "car";
  const identityDocumentType = useWatch({ control, name: "identityDocumentType" }) || "pesel";
  const formData = useWatch({ control, name: "payload" }) || {};
  const declarationsReviewed = useWatch({ control, name: "declarationsReviewed" }) || false;
  const imagePublicationConsent =
    useWatch({ control, name: "consents.image_publication" }) || false;

  function updateField(fieldName, value) {
    setValue(`payload.${fieldName}`, value, { shouldDirty: true });
  }

  function updateMinor(minorIndex, fieldName, value) {
    setValue(`minors.${minorIndex}.${fieldName}`, value, { shouldDirty: true });
  }

  function addMinor() {
    append(createEmptyMinor());
  }

  function removeMinor(index) {
    if (minors.length === 1) {
      return;
    }
    remove(index);
  }

  function handleIdentityDocumentTypeChange(value) {
    setValue("identityDocumentType", value, { shouldDirty: true });
    if (value === "pesel") {
      setValue("payload.id_card_series", "");
      setValue("payload.id_card_number", "");
      return;
    }
    setValue("payload.pesel", "");
  }

  function handleParticipantRoleChange(value) {
    setValue("participantRole", value, { shouldDirty: true });
    replace([createEmptyMinor()]);

    if (value !== "legal_guardian") {
      const payload = { ...getValues("payload") };
      for (const fieldName of GUARDIAN_FIELDS) {
        delete payload[fieldName];
      }
      setValue("payload", payload, { shouldDirty: true });
    }
  }

  function handleValidSubmit(data) {
    const basePayload = buildPayloadJson(data.payload, schema, data.identityDocumentType, {
      excludeVehicleFields: data.participantRole === "legal_guardian",
    });

    setValidationErrors([]);

    if (data.participantRole === "legal_guardian") {
      onSubmit(
        data.minors.map((minor) =>
          buildSubmissionPayload({
            basePayload,
            minor,
            participantRole: data.participantRole,
            vehicleType: data.vehicleType,
            consents: data.consents,
            signatureImageBase64: data.signatureImageBase64,
          }),
        ),
      );
      return;
    }

    onSubmit(
      buildSubmissionPayload({
        basePayload,
        participantRole: data.participantRole,
        vehicleType: data.vehicleType,
        consents: data.consents,
        signatureImageBase64: data.signatureImageBase64,
      }),
    );
  }

  function handleInvalidSubmit() {
    const result = formSchema.safeParse(getValues());
    setValidationErrors(flattenZodErrors(result));
  }

  return (
    <form className="guest-form" onSubmit={handleSubmit(handleValidSubmit, handleInvalidSubmit)}>
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
            onChange={(value) => setValue("vehicleType", value, { shouldDirty: true })}
          />
        )}
      </fieldset>

      <PersonalDataSection
        title={`II. Dane ${participantRole === "legal_guardian" ? "opiekuna" : "uczestnika"}`}
        hint={participantRole === "legal_guardian" ? "Wypełnij swoje dane jako opiekun prawny." : null}
        fieldNames={PERSONAL_DATA_FIELDS}
        properties={properties}
        schema={schema}
        formData={formData}
        updateField={updateField}
      />
      <fieldset className="form-card">
        <legend>Dokument tożsamości</legend>
        <IdentityDocumentSection
          properties={properties}
          identityDocumentType={identityDocumentType}
          onIdentityDocumentTypeChange={handleIdentityDocumentTypeChange}
          formData={formData}
          updateField={updateField}
        />
      </fieldset>

      {participantRole !== "legal_guardian" && (
        <VehicleDataSection
          properties={properties}
          schema={schema}
          formData={formData}
          updateField={updateField}
        />
      )}

      <fieldset className="form-card">
        <legend>IV. Oświadczenia oraz akceptacja ryzyka</legend>
        <p className="hint">Zapoznaj się z pełną treścią poniżej. Przewiń tekst do końca przed wysłaniem.</p>
        <DeclarationsPanel
          reviewed={declarationsReviewed}
          onReviewed={() => setValue("declarationsReviewed", true, { shouldDirty: true })}
        />
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
                    onClick={() => removeMinor(index)}
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
                onChange={(value) => updateMinor(index, "guardian_relation", value)}
              />
              <div className="field-row">
                <label className="field">
                  <span>Imię podopiecznego</span>
                  <input
                    type="text"
                    value={minor.minor_first_name}
                    onChange={(event) => updateMinor(index, "minor_first_name", event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Nazwisko podopiecznego</span>
                  <input
                    type="text"
                    value={minor.minor_last_name}
                    onChange={(event) => updateMinor(index, "minor_last_name", event.target.value)}
                    required
                  />
                </label>
              </div>
              {renderMinorVehicleFields(minor, properties, (_minorId, fieldName, value) =>
                updateMinor(index, fieldName, value),
              )}
            </div>
          ))}
          <button className="secondary-button" type="button" onClick={addMinor}>
            Dodaj podopiecznego
          </button>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={imagePublicationConsent}
              onChange={(event) =>
                setValue("consents.image_publication", event.target.checked, { shouldDirty: true })
              }
            />
            <span>{IMAGE_PUBLICATION_CONSENT_TEXT}</span>
          </label>
        </fieldset>
      )}

      <SignatureSection
        properties={properties}
        formData={formData}
        updateField={updateField}
        signatureLabel="Czytelny podpis uczestnika / opiekuna"
        onSignatureChange={(value) => setValue("signatureImageBase64", value, { shouldDirty: true })}
        submitting={submitting}
      />

      <FormValidationAlert errors={validationErrors} />

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
