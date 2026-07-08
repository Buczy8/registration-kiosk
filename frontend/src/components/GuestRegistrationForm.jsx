import { FormProvider } from "react-hook-form";

import { FORM_SUBTITLE } from "../content/participantDeclarations.js";
import { useRegistrationForm } from "../hooks/useRegistrationForm.js";
import {
  PERSONAL_DATA_FIELDS,
  ParticipantRole,
} from "../lib/registrationFormShared.js";
import DeclarationsSection from "./form/DeclarationsSection.jsx";
import FormValidationSummary from "./form/FormValidationSummary.jsx";
import GuardianMinorsSection from "./form/GuardianMinorsSection.jsx";
import IdentityDocumentSection from "./form/IdentityDocumentSection.jsx";
import ParticipantRoleSection from "./form/ParticipantRoleSection.jsx";
import PersonalDataSection from "./form/PersonalDataSection.jsx";
import SignatureSection from "./form/SignatureSection.jsx";
import VehicleDataSection from "./form/VehicleDataSection.jsx";

export default function GuestRegistrationForm({ form, onSubmit, submitting, submitError }) {
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
    mode: "guest",
  });

  function handleValidSubmit(data) {
    const submissions = buildSubmissions(data);
    onSubmit(submissions.length === 1 ? submissions[0] : submissions);
  }

  const isGuardian = participantRole === ParticipantRole.LEGAL_GUARDIAN;

  return (
    <FormProvider {...methods}>
      <form className="guest-form" onSubmit={methods.handleSubmit(handleValidSubmit)}>
        <header className="form-header">
          <p className="eyebrow">Kiosk gościa</p>
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

        {isGuardian && <GuardianMinorsSection properties={properties} />}

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

        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "Wysyłanie..." : "Wyślij"}
        </button>
      </form>
    </FormProvider>
  );
}
