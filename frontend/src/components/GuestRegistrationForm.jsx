import { useCallback, useEffect, useState } from "react";
import { FormProvider, Controller } from "react-hook-form";

import { listRelatedPersons } from "../api/account.js";
import { getFormPrefill } from "../api/auth.js";
import { FORM_SUBTITLE, IMAGE_PUBLICATION_CONSENT_TEXT } from "../content/participantDeclarations.js";
import { useRegistrationForm } from "../hooks/useRegistrationForm.js";
import {
  PERSONAL_DATA_FIELDS,
  ParticipantRole,
  createEmptyMinor,
  generateSafeUUID,
  inferIdentityDocumentType,
  mapPrefillToFormData,
} from "../lib/registrationFormShared.js";
import DeclarationsSection from "./form/DeclarationsSection.jsx";
import FormValidationSummary from "./form/FormValidationSummary.jsx";
import GuardianMinorsSection from "./form/GuardianMinorsSection.jsx";
import IdentityDocumentSection from "./form/IdentityDocumentSection.jsx";
import ParticipantRoleSection from "./form/ParticipantRoleSection.jsx";
import PersonalDataSection from "./form/PersonalDataSection.jsx";
import SignatureSection from "./form/SignatureSection.jsx";
import VehicleDataSection from "./form/VehicleDataSection.jsx";

export default function GuestRegistrationForm({
  form,
  mode = "guest",
  role,
  vehicleType,
  onSubmit,
  onBack,
  submitting,
  submitError,
  onRoleChange,
  onVehicleTypeChange,
}) {
  const isAccountMode = mode === "account";
  const useGuardianMinorPayload =
    isAccountMode && role === ParticipantRole.LEGAL_GUARDIAN;

  const {
    methods,
    properties,
    schema,
    participantRole,
    handleIdentityDocumentTypeChange,
    handleParticipantRoleChange,
    buildSubmissions,
  } = useRegistrationForm({
    schemaJson: form.schema_json,
    mode,
    role,
    vehicleType,
    useGuardianMinorPayload,
  });

  const [loadingPrefill, setLoadingPrefill] = useState(isAccountMode);
  const [prefillError, setPrefillError] = useState(null);

  const loadPrefill = useCallback(async () => {
    if (!isAccountMode) {
      return;
    }

    setLoadingPrefill(true);
    setPrefillError(null);
    try {
      const relatedPersons = await listRelatedPersons();
      const effectiveRole =
        role || (relatedPersons.length > 0 ? ParticipantRole.LEGAL_GUARDIAN : ParticipantRole.DRIVER);
      const effectiveVehicleType = vehicleType || "car";
      const prefill = await getFormPrefill(effectiveRole, effectiveVehicleType);
      const mapped = mapPrefillToFormData(prefill);
      let minors = [];
      let imagePublicationConsent = prefill?.image_publication_consent || false;

      if (effectiveRole === ParticipantRole.LEGAL_GUARDIAN) {
        minors = relatedPersons.map((person) => ({
          id: generateSafeUUID(),
          related_person_id: person.id,
          guardian_relation: person.guardian_relation || "",
          minor_first_name: person.first_name || "",
          minor_last_name: person.last_name || "",
          vehicle_type: person.vehicle_type || effectiveVehicleType,
          vehicle_brand: person.vehicle_brand || "",
          vehicle_model: person.vehicle_model || "",
          vehicle_registration_number:
            person.vehicle_registration_number || "",
          image_publication: person.image_publication_consent || false,
        }));
        if (minors.length === 0) {
          minors = [createEmptyMinor()];
        }
      }

      const resetValues = {
        participantRole: effectiveRole,
        vehicleType: effectiveVehicleType,
        identityDocumentType: inferIdentityDocumentType(mapped),
        payload: mapped,
        declarationsReviewed: false,
        signatureImageBase64: "",
        minors,
        consents: { image_publication: imagePublicationConsent },
      };

      methods.reset(resetValues);
    } catch (error) {
      setPrefillError(error.message || "Nie udało się pobrać danych profilu.");
    } finally {
      setLoadingPrefill(false);
    }
  }, [isAccountMode, methods, role, vehicleType]);

  useEffect(() => {
    loadPrefill();
  }, [loadPrefill]);

  const watchedRole = methods.watch("participantRole");
  const watchedVehicleType = methods.watch("vehicleType");

  useEffect(() => {
    if (watchedRole && onRoleChange && watchedRole !== role) {
      onRoleChange(watchedRole);
    }
  }, [watchedRole, role, onRoleChange]);

  useEffect(() => {
    if (watchedVehicleType && onVehicleTypeChange && watchedVehicleType !== vehicleType) {
      onVehicleTypeChange(watchedVehicleType);
    }
  }, [watchedVehicleType, vehicleType, onVehicleTypeChange]);

  function handleValidSubmit(data) {
    const submissions = buildSubmissions(data);
    onSubmit(submissions.length === 1 ? submissions[0] : submissions);
  }

  const isGuardian = participantRole === ParticipantRole.LEGAL_GUARDIAN;

  if (loadingPrefill) {
    return <p className="status-card">Ładowanie danych profilu...</p>;
  }

  if (prefillError) {
    return (
      <div className="status-card alert" role="alert">
        <p>Nie udało się pobrać danych: {prefillError}</p>
        <div className="actions">
          {onBack && (
            <button className="secondary-button" type="button" onClick={onBack}>
              &larr; Wróć
            </button>
          )}
          <button className="primary-button" type="button" onClick={loadPrefill}>
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <FormProvider {...methods}>
      <form className="guest-form" onSubmit={methods.handleSubmit(handleValidSubmit)}>
        <header className="form-header">
          <p className="eyebrow">{isAccountMode ? "Konto użytkownika" : "Kiosk gościa"}</p>
          <h1>Oświadczenie uczestnika – Autodrom Biłgoraj</h1>
          <p>{FORM_SUBTITLE}</p>
          <p className="hint">Wersja formularza: {form.version}</p>
        </header>

        <fieldset className="form-card">
          <legend>I. Status uczestnika oraz rodzaj jazd</legend>
          <ParticipantRoleSection onParticipantRoleChange={handleParticipantRoleChange} />
        </fieldset>

        <PersonalDataSection
          title={`II. Dane ${isGuardian ? "opiekuna" : "uczestnika"}`}
          hint={isGuardian ? "Wypełnij swoje dane jako opiekun prawny." : null}
          fieldNames={PERSONAL_DATA_FIELDS}
          properties={properties}
          schema={schema}
        />

        <fieldset className="form-card">
          <legend>Dokument tożsamości</legend>
          <IdentityDocumentSection
            properties={properties}
            onIdentityDocumentTypeChange={handleIdentityDocumentTypeChange}
          />
        </fieldset>

        {!isGuardian && <VehicleDataSection properties={properties} schema={schema} />}

        <DeclarationsSection />

        {isGuardian && (
          <GuardianMinorsSection
            properties={properties}
            allowMultiple
          />
        )}

        {!isGuardian && (
          <fieldset className="form-card">
            <legend>Zgoda na publikację wizerunku</legend>
            <Controller
              control={methods.control}
              name="consents.image_publication"
              render={({ field }) => (
                <label className="checkbox-field">
                  <input type="checkbox" checked={Boolean(field.value)} onChange={field.onChange} />
                  <span>{IMAGE_PUBLICATION_CONSENT_TEXT}</span>
                </label>
              )}
            />
          </fieldset>
        )}

        <SignatureSection
          properties={properties}
          signatureLabel="Czytelny podpis uczestnika / opiekuna"
          submitting={submitting}
        />

        <FormValidationSummary />

        {submitError && (
          <div className="alert" role="alert">
            <p>Błąd wysyłki: {submitError}</p>
          </div>
        )}

        <div className="actions">
          {onBack && (
            <button className="secondary-button" type="button" onClick={onBack} disabled={submitting}>
              &larr; Wróć
            </button>
          )}
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Wysyłanie..." : "Wyślij"}
          </button>
        </div>
      </form>
    </FormProvider>
  );
}
