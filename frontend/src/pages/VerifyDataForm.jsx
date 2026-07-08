import { useCallback, useEffect, useState } from "react";
import { FormProvider } from "react-hook-form";

import { getFormPrefill } from "../api/auth.js";
import { FORM_SUBTITLE } from "../content/participantDeclarations.js";
import DeclarationsSection from "../components/form/DeclarationsSection.jsx";
import FormValidationSummary from "../components/form/FormValidationSummary.jsx";
import IdentityDocumentSection from "../components/form/IdentityDocumentSection.jsx";
import PersonalDataSection from "../components/form/PersonalDataSection.jsx";
import SignatureSection from "../components/form/SignatureSection.jsx";
import VehicleDataSection from "../components/form/VehicleDataSection.jsx";
import { useRegistrationForm } from "../hooks/useRegistrationForm.js";
import {
  PERSONAL_DATA_FIELDS,
  getRoleLabel,
  getVehicleLabel,
  inferIdentityDocumentType,
  mapPrefillToFormData,
} from "../lib/registrationFormShared.js";

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
  const {
    methods,
    properties,
    schema,
    handleIdentityDocumentTypeChange,
    buildSubmissions,
  } = useRegistrationForm({
    schemaJson: form.schema_json,
    mode: "account",
    role,
    vehicleType,
  });

  const [loadingPrefill, setLoadingPrefill] = useState(true);
  const [prefillError, setPrefillError] = useState(null);

  const loadPrefill = useCallback(async () => {
    setLoadingPrefill(true);
    setPrefillError(null);
    try {
      const prefill = await getFormPrefill(token, role, vehicleType);
      const mapped = mapPrefillToFormData(prefill);
      methods.reset({
        participantRole: role,
        vehicleType,
        identityDocumentType: inferIdentityDocumentType(mapped),
        payload: mapped,
        declarationsReviewed: false,
        signatureImageBase64: "",
        minors: [],
        consents: { image_publication: false },
      });
    } catch (error) {
      setPrefillError(error.message || "Nie udało się pobrać danych profilu.");
    } finally {
      setLoadingPrefill(false);
    }
  }, [methods, role, token, vehicleType]);

  useEffect(() => {
    loadPrefill();
  }, [loadPrefill]);

  function handleValidSubmit(data) {
    onSubmit(buildSubmissions(data)[0]);
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
    <FormProvider {...methods}>
      <form className="guest-form" onSubmit={methods.handleSubmit(handleValidSubmit)}>
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

        <PersonalDataSection
          title="Dane uczestnika"
          hint="Sprawdź i popraw dane przed wysłaniem formularza."
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

        <VehicleDataSection properties={properties} schema={schema} />

        <DeclarationsSection legend="Oświadczenia oraz akceptacja ryzyka" />

        <SignatureSection
          properties={properties}
          signatureLabel="Czytelny podpis uczestnika"
          submitting={submitting}
        />

        <FormValidationSummary />

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
    </FormProvider>
  );
}
