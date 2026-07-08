import { Controller, useFormContext } from "react-hook-form";

import {
  IDENTITY_DOCUMENT_TYPES,
  IdentityDocumentType,
} from "../../lib/registrationFormShared.js";
import RadioGroup from "../RadioGroup.jsx";
import SchemaTextField from "./SchemaTextField.jsx";

export default function IdentityDocumentSection({ properties, onIdentityDocumentTypeChange }) {
  const { control, watch } = useFormContext();
  const identityDocumentType = watch("identityDocumentType");

  return (
    <div className="identity-fields">
      <Controller
        control={control}
        name="identityDocumentType"
        render={({ field }) => (
          <RadioGroup
            legend="Dokument tożsamości"
            name="identity_document_type"
            options={IDENTITY_DOCUMENT_TYPES}
            value={field.value}
            onChange={(value) => {
              field.onChange(value);
              onIdentityDocumentTypeChange(value);
            }}
          />
        )}
      />
      {identityDocumentType === IdentityDocumentType.PESEL ? (
        <SchemaTextField name="payload.pesel" property={properties.pesel} />
      ) : (
        <div className="field-row">
          <SchemaTextField
            name="payload.id_card_series"
            property={properties.id_card_series || { title: "Seria dowodu osobistego" }}
          />
          <SchemaTextField
            name="payload.id_card_number"
            property={properties.id_card_number || { title: "Numer dowodu osobistego" }}
          />
        </div>
      )}
    </div>
  );
}
