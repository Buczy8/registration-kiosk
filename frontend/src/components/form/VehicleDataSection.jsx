import { VEHICLE_DATA_FIELDS } from "../../lib/registrationFormShared.js";
import SchemaFieldsList from "./SchemaFieldsList.jsx";

export default function VehicleDataSection({ properties, schema }) {
  return (
    <fieldset className="form-card">
      <legend>Dane pojazdu</legend>
      <p className="hint">Pola opcjonalne — wypełnij, jeśli dotyczy.</p>
      <SchemaFieldsList
        fieldNames={VEHICLE_DATA_FIELDS}
        properties={properties}
        schema={schema}
        forceOptional
      />
    </fieldset>
  );
}
