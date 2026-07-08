import { useEffect, useState } from "react";
import { Controller, useFieldArray, useFormContext, useWatch } from "react-hook-form";

import {
  GUARDIAN_DECLARATION_INTRO,
  IMAGE_PUBLICATION_CONSENT_TEXT,
} from "../../content/participantDeclarations.js";
import { GUARDIAN_RELATIONS, createEmptyMinor } from "../../lib/registrationFormShared.js";
import RadioGroup from "../RadioGroup.jsx";
import MinorVehicleSection from "./MinorVehicleSection.jsx";
import SchemaTextField from "./SchemaTextField.jsx";

export default function GuardianMinorsSection({ properties, allowMultiple = true }) {
  const { control, formState: { errors } } = useFormContext();
  const { fields, append, remove } = useFieldArray({ control, name: "minors" });
  const minors = useWatch({ control, name: "minors" }) || [];
  const [activeIndex, setActiveIndex] = useState(0);
  const minorsError = errors.minors?.message || errors.minors?.root?.message;

  useEffect(() => {
    if (fields.length === 0) {
      setActiveIndex(0);
      return;
    }
    if (activeIndex >= fields.length) {
      setActiveIndex(fields.length - 1);
    }
  }, [activeIndex, fields.length]);

  function addMinor() {
    append(createEmptyMinor());
    setActiveIndex(fields.length);
  }

  function removeMinor(index) {
    if (fields.length === 1) {
      return;
    }
    remove(index);
    setActiveIndex((current) => {
      if (current > index) {
        return current - 1;
      }
      if (current === index) {
        return Math.max(0, current - 1);
      }
      return current;
    });
  }

  const activeField = fields[activeIndex];

  return (
    <fieldset className="form-card">
      <legend>V. Dla opiekunów prawnych (osoby niepełnoletnie)</legend>
      <p className="guardian-declaration">{GUARDIAN_DECLARATION_INTRO}</p>
      <p className="hint">
        Podopieczni są wysyłani jako osobne zgłoszenia, ale podpis składasz raz dla całego formularza.
      </p>

      {minorsError && (
        <p className="field-error" role="alert">
          {minorsError}
        </p>
      )}

      <div className="minor-table-card">
        <div className="minor-table-header">
          <h3>Podopieczni</h3>
          {allowMultiple && (
            <button className="primary-button minor-add-button" type="button" onClick={addMinor}>
              + Dodaj
            </button>
          )}
        </div>

        <table className="minor-table">
          <thead>
            <tr>
              <th>Imię i nazwisko</th>
              <th>Akcja</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((minor, index) => {
              const current = minors[index] || {};
              const fullName = `${current.minor_first_name || ""} ${current.minor_last_name || ""}`.trim();
              return (
                <tr className={index === activeIndex ? "is-active" : ""} key={minor.id}>
                  <td>{fullName || `Podopieczny ${index + 1}`}</td>
                  <td className="minor-table-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => setActiveIndex(index)}
                    >
                      Edytuj
                    </button>
                    {allowMultiple && fields.length > 1 && (
                      <button
                        className="secondary-button minor-remove-button"
                        type="button"
                        onClick={() => removeMinor(index)}
                      >
                        Usuń
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {activeField && (
        <div className="minor-card" key={activeField.id}>
          <div className="minor-card-header">
            <h3>Edycja podopiecznego</h3>
          </div>

          <Controller
            control={control}
            name={`minors.${activeIndex}.guardian_relation`}
            render={({ field }) => (
              <RadioGroup
                legend="Typ opiekuna"
                name={`guardian_relation_${activeField.id}`}
                options={GUARDIAN_RELATIONS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />

          <div className="field-row">
            <SchemaTextField
              name={`minors.${activeIndex}.minor_first_name`}
              property={{ title: "Imię podopiecznego" }}
            />
            <SchemaTextField
              name={`minors.${activeIndex}.minor_last_name`}
              property={{ title: "Nazwisko podopiecznego" }}
            />
          </div>

          <MinorVehicleSection index={activeIndex} properties={properties} />
        </div>
      )}

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
