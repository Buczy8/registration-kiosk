import { useFormContext } from "react-hook-form";

import { getInputType, getNestedError, isVehicleField } from "../../lib/registrationFormShared.js";

export default function SchemaTextField({ name, property, schema, forceOptional = false }) {
  const {
    register,
    formState: { errors },
  } = useFormContext();

  const fieldName = name.split(".").pop();
  const required =
    !forceOptional &&
    !isVehicleField(fieldName) &&
    (schema?.required || []).includes(fieldName);
  const error = getNestedError(errors, name);
  const errorId = `${name.replace(/\./g, "-")}-error`;

  return (
    <label className={`field${error ? " field--invalid" : ""}`}>
      <span>
        {property?.title || fieldName}
        {required ? " *" : ""}
      </span>
      <input
        type={getInputType(property || {})}
        pattern={property?.pattern}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? errorId : undefined}
        {...register(name)}
      />
      {error?.message && (
        <span id={errorId} className="field-error" role="alert">
          {error.message}
        </span>
      )}
    </label>
  );
}
