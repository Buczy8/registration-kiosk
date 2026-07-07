import { renderFields } from "../registrationFormFields.jsx";

export default function PersonalDataSection({
  title,
  hint,
  fieldNames,
  properties,
  schema,
  formData,
  updateField,
}) {
  return (
    <fieldset className="form-card">
      <legend>{title}</legend>
      {hint && <p className="hint">{hint}</p>}
      {renderFields(fieldNames, properties, schema, formData, updateField)}
    </fieldset>
  );
}
