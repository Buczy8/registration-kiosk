import { Controller, useFieldArray, useFormContext } from "react-hook-form";

import {
  GUARDIAN_DECLARATION_INTRO,
  IMAGE_PUBLICATION_CONSENT_TEXT,
} from "../../content/participantDeclarations.js";
import { GUARDIAN_RELATIONS, createEmptyMinor } from "../../lib/registrationFormShared.js";
import RadioGroup from "../RadioGroup.jsx";
import MinorVehicleSection from "./MinorVehicleSection.jsx";
import SchemaTextField from "./SchemaTextField.jsx";

export default function GuardianMinorsSection({ properties }) {
  const { control, formState: { errors } } = useFormContext();
  const { fields, append, remove } = useFieldArray({ control, name: "minors" });
  const minorsError = errors.minors?.message || errors.minors?.root?.message;

  function addMinor() {
    append(createEmptyMinor());
  }

  function removeMinor(index) {
    if (fields.length === 1) {
      return;
    }
    remove(index);
  }

  return (
    <fieldset className="form-card">
      <legend>V. Dla opiekunów prawnych (osoby niepełnoletnie)</legend>
      <p className="guardian-declaration">{GUARDIAN_DECLARATION_INTRO}</p>
      <p className="hint">
        Dodaj jednego lub więcej podopiecznych. Dla każdego zostanie utworzone osobne zgłoszenie i PDF.
      </p>

      {minorsError && (
        <p className="field-error" role="alert">
          {minorsError}
        </p>
      )}

      {fields.map((minor, index) => (
        <div className="minor-card" key={minor.id}>
          <div className="minor-card-header">
            <h3>Podopieczny {index + 1}</h3>
            {fields.length > 1 && (
              <button
                className="secondary-button minor-remove-button"
                type="button"
                onClick={() => removeMinor(index)}
              >
                Usuń
              </button>
            )}
          </div>

          <Controller
            control={control}
            name={`minors.${index}.guardian_relation`}
            render={({ field }) => (
              <RadioGroup
                legend="Typ opiekuna"
                name={`guardian_relation_${minor.id}`}
                options={GUARDIAN_RELATIONS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />

          <div className="field-row">
            <SchemaTextField name={`minors.${index}.minor_first_name`} property={{ title: "Imię podopiecznego" }} />
            <SchemaTextField
              name={`minors.${index}.minor_last_name`}
              property={{ title: "Nazwisko podopiecznego" }}
            />
          </div>

          <MinorVehicleSection index={index} properties={properties} />
        </div>
      ))}

      <button className="secondary-button" type="button" onClick={addMinor}>
        Dodaj podopiecznego
      </button>

      <Controller
        control={control}
        name="consents.image_publication"
        render={({ field }) => (
          <label className="checkbox-field">
            <input type="checkbox" checked={Boolean(field.value)} onChange={field.onChange} />
            <span>{IMAGE_PUBLICATION_CONSENT_TEXT}</span>
          </label>
        )}
      />
    </fieldset>
  );
}
