import { renderFields } from "../registrationFormFields.jsx";

export default function VehicleDataSection({ properties, schema, formData, updateField }) {
  return (
    <fieldset className="form-card">
      <legend>Dane pojazdu</legend>
      <p className="hint">Pola opcjonalne — wypełnij, jeśli dotyczy.</p>
      {renderFields(["vehicle_brand", "vehicle_model", "vehicle_registration_number"], properties, schema, formData, updateField, {
        forceOptional: true,
      })}
    </fieldset>
  );
}
