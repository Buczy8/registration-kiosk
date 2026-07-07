import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { getFormPrefill } from "../api/auth.js";
import { FORM_SUBTITLE } from "../content/participantDeclarations.js";
import {
  PERSONAL_DATA_FIELDS,
  buildPayloadJson,
  buildSubmissionPayload,
  getRoleLabel,
  getVehicleLabel,
  inferIdentityDocumentType,
  mapPrefillToFormData,
} from "../lib/registrationFormShared.js";
import { buildFormSchema, flattenZodErrors } from "../lib/registrationSchemas.js";
import DeclarationsPanel from "../components/DeclarationsPanel.jsx";
import FormValidationAlert from "../components/form/FormValidationAlert.jsx";
import IdentityDocumentSection from "../components/form/IdentityDocumentSection.jsx";
import PersonalDataSection from "../components/form/PersonalDataSection.jsx";
import SignatureSection from "../components/form/SignatureSection.jsx";
import VehicleDataSection from "../components/form/VehicleDataSection.jsx";

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
  const schema = useMemo(() => form.schema_json || {}, [form.schema_json]);
  const properties = schema.properties || {};
  const formSchema = useMemo(
    () => buildFormSchema({ schemaJson: schema, requireRoleSelection: false }),
    [schema],
  );

  const [validationErrors, setValidationErrors] = useState([]);
  const [loadingPrefill, setLoadingPrefill] = useState(true);
  const [prefillError, setPrefillError] = useState(null);

  const {
    control,
    handleSubmit,
    setValue,
    getValues,
    reset,
  } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      participantRole: role,
      vehicleType,
      identityDocumentType: "pesel",
      payload: {},
      declarationsReviewed: false,
      signatureImageBase64: "",
      minors: [],
    },
  });

  const formData = useWatch({ control, name: "payload" }) || {};
  const identityDocumentType = useWatch({ control, name: "identityDocumentType" }) || "pesel";
  const declarationsReviewed = useWatch({ control, name: "declarationsReviewed" }) || false;

  const loadPrefill = useCallback(async () => {
    setLoadingPrefill(true);
    setPrefillError(null);
    try {
      const prefill = await getFormPrefill(token, role, vehicleType);
      const mapped = mapPrefillToFormData(prefill);
      reset({
        participantRole: role,
        vehicleType,
        identityDocumentType: inferIdentityDocumentType(mapped),
        payload: mapped,
        declarationsReviewed: false,
        signatureImageBase64: "",
        minors: [],
      });
      setValidationErrors([]);
    } catch (error) {
      setPrefillError(error.message || "Nie udało się pobrać danych profilu.");
    } finally {
      setLoadingPrefill(false);
    }
  }, [token, role, vehicleType, reset]);

  useEffect(() => {
    loadPrefill();
  }, [loadPrefill]);

  function updateField(fieldName, value) {
    setValue(`payload.${fieldName}`, value, { shouldDirty: true });
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

  const handleValidSubmit = (data) => {
    const basePayload = buildPayloadJson(data.payload, schema, data.identityDocumentType);
    setValidationErrors([]);
    onSubmit(
      buildSubmissionPayload({
        basePayload,
        participantRole: role,
        vehicleType,
        signatureImageBase64: data.signatureImageBase64,
      }),
    );
  };

  const handleInvalidSubmit = () => {
    const result = formSchema.safeParse(getValues());
    setValidationErrors(flattenZodErrors(result));
  };

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
    <form className="guest-form" onSubmit={handleSubmit(handleValidSubmit, handleInvalidSubmit)}>
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
      <VehicleDataSection properties={properties} schema={schema} formData={formData} updateField={updateField} />

      <fieldset className="form-card">
        <legend>Oświadczenia oraz akceptacja ryzyka</legend>
        <p className="hint">Zapoznaj się z pełną treścią poniżej. Przewiń tekst do końca przed wysłaniem.</p>
        <DeclarationsPanel
          reviewed={declarationsReviewed}
          onReviewed={() => setValue("declarationsReviewed", true, { shouldDirty: true })}
        />
        {!declarationsReviewed && (
          <p className="review-hint">Przewiń oświadczenia do końca, aby wysłać formularz.</p>
        )}
      </fieldset>

      <SignatureSection
        properties={properties}
        formData={formData}
        updateField={updateField}
        signatureLabel="Czytelny podpis uczestnika"
        onSignatureChange={(value) => setValue("signatureImageBase64", value, { shouldDirty: true })}
        submitting={submitting}
      />
      <FormValidationAlert errors={validationErrors} />

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
