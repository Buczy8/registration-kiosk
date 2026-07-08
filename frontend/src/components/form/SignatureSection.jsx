import { Controller, useFormContext } from "react-hook-form";

import { SIGNATURE_PLACE_FIELD } from "../../lib/registrationFormShared.js";
import SignaturePad from "../SignaturePad.jsx";
import SchemaTextField from "./SchemaTextField.jsx";

export default function SignatureSection({ properties, signatureLabel, submitting }) {
  const { control } = useFormContext();

  return (
    <fieldset className="form-card">
      <legend>Data i miejscowość oraz podpis</legend>
      <div className="signature-section">
        <SchemaTextField
          name={`payload.${SIGNATURE_PLACE_FIELD}`}
          property={properties.signature_place || { title: "Data i miejscowość" }}
        />
        <div className="signature-pad-field">
          <p className="signature-footer-label">{signatureLabel}</p>
          <Controller
            control={control}
            name="signatureImageBase64"
            render={({ field }) => (
              <SignaturePad onChange={field.onChange} disabled={submitting} />
            )}
          />
        </div>
      </div>
    </fieldset>
  );
}
