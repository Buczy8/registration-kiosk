import SchemaTextField from "./SchemaTextField.jsx";

export default function SchemaFieldsList({
  fieldNames,
  properties,
  schema,
  namePrefix = "payload",
  forceOptional = false,
}) {
  return fieldNames
    .filter((fieldName) => properties[fieldName])
    .map((fieldName) => (
      <SchemaTextField
        key={fieldName}
        name={`${namePrefix}.${fieldName}`}
        property={properties[fieldName]}
        schema={schema}
        forceOptional={forceOptional}
      />
    ));
}
