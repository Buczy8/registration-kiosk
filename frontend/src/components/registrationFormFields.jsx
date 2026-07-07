import {
  VEHICLE_DATA_FIELDS,
  VEHICLE_TYPES,
  getInputType,
  isVehicleField,
} from "../lib/registrationFormShared.js";
import RadioGroup from "./RadioGroup.jsx";

export function renderFields(
  fieldNames,
  properties,
  schema,
  formData,
  updateField,
  { forceOptional = false } = {},
) {
  return fieldNames
    .filter((fieldName) => properties[fieldName])
    .map((fieldName) => {
      const property = properties[fieldName];
      const required =
        !forceOptional &&
        !isVehicleField(fieldName) &&
        (schema.required || []).includes(fieldName);
      return (
        <label className="field" key={fieldName}>
          <span>{property.title || fieldName}</span>
          <input
            type={getInputType(property)}
            value={formData[fieldName] || ""}
            onChange={(event) => updateField(fieldName, event.target.value)}
            pattern={property.pattern}
            required={required}
          />
        </label>
      );
    });
}

export function renderMinorVehicleFields(minor, properties, updateMinor) {
  return (
    <div className="minor-vehicle-fields">
      <p className="identity-label">Dane pojazdu (opcjonalnie)</p>
      <RadioGroup
        legend="Rodzaj pojazdu"
        name={`vehicle_type_${minor.id}`}
        options={VEHICLE_TYPES}
        value={minor.vehicle_type}
        onChange={(value) => updateMinor(minor.id, "vehicle_type", value)}
      />
      <div className="field-row">
        <label className="field">
          <span>{properties.vehicle_brand?.title || "Marka pojazdu"}</span>
          <input
            type="text"
            value={minor.vehicle_brand}
            onChange={(event) => updateMinor(minor.id, "vehicle_brand", event.target.value)}
          />
        </label>
        <label className="field">
          <span>{properties.vehicle_model?.title || "Model pojazdu"}</span>
          <input
            type="text"
            value={minor.vehicle_model}
            onChange={(event) => updateMinor(minor.id, "vehicle_model", event.target.value)}
          />
        </label>
      </div>
      <label className="field">
        <span>{properties.vehicle_registration_number?.title || "Numer rejestracyjny"}</span>
        <input
          type="text"
          value={minor.vehicle_registration_number}
          onChange={(event) =>
            updateMinor(minor.id, "vehicle_registration_number", event.target.value)
          }
        />
      </label>
    </div>
  );
}

export { VEHICLE_DATA_FIELDS };
