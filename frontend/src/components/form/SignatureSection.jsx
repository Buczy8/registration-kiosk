import { SIGNATURE_PLACE_FIELD } from "../../lib/registrationFormShared.js";
import SignaturePad from "../SignaturePad.jsx";

export default function SignatureSection({
  properties,
  formData,
  updateField,
  signatureLabel,
  onSignatureChange,
  submitting,
}) {
  return (
    <fieldset className="form-card">
      <legend>Data i miejscowość oraz podpis</legend>
      <div className="signature-section">
        <label className="field signature-place-field">
          <span>{properties.signature_place?.title || "Data i miejscowość"}</span>
          <input
            type="text"
            value={formData[SIGNATURE_PLACE_FIELD] || ""}
            onChange={(event) => updateField(SIGNATURE_PLACE_FIELD, event.target.value)}
            placeholder="np. Biłgoraj, 03.07.2026"
            required
          />
        </label>
        <div className="signature-pad-field">
          <p className="signature-footer-label">{signatureLabel}</p>
          <SignaturePad onChange={onSignatureChange} disabled={submitting} />
        </div>
      </div>
    </fieldset>
  );
}
