import RadioGroup from "../RadioGroup.jsx";
import { IDENTITY_DOCUMENT_TYPES } from "../../lib/registrationFormShared.js";

export default function IdentityDocumentSection({
  properties,
  identityDocumentType,
  onIdentityDocumentTypeChange,
  formData,
  updateField,
}) {
  return (
    <div className="identity-fields">
      <RadioGroup
        legend="Dokument tożsamości"
        name="identity_document_type"
        options={IDENTITY_DOCUMENT_TYPES}
        value={identityDocumentType}
        onChange={onIdentityDocumentTypeChange}
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
  );
}
