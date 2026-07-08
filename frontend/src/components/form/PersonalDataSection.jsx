import SchemaFieldsList from "./SchemaFieldsList.jsx";

export default function PersonalDataSection({ title, hint, fieldNames, properties, schema }) {
  return (
    <fieldset className="form-card">
      <legend>{title}</legend>
      {hint && <p className="hint">{hint}</p>}
      <SchemaFieldsList fieldNames={fieldNames} properties={properties} schema={schema} />
    </fieldset>
  );
}
