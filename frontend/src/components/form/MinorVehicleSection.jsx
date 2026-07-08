import { Controller, useFormContext } from "react-hook-form";

import { VEHICLE_TYPES } from "../../lib/registrationFormShared.js";
import RadioGroup from "../RadioGroup.jsx";
import SchemaTextField from "./SchemaTextField.jsx";

export default function MinorVehicleSection({ index, properties }) {
  const { control } = useFormContext();
  const prefix = `minors.${index}`;

  return (
    <div className="minor-vehicle-fields">
      <p className="identity-label">Dane pojazdu (opcjonalnie)</p>
      <Controller
        control={control}
        name={`${prefix}.vehicle_type`}
        render={({ field }) => (
          <RadioGroup
            legend="Rodzaj pojazdu"
            name={`vehicle_type_${index}`}
            options={VEHICLE_TYPES}
            value={field.value}
            onChange={field.onChange}
          />
        )}
      />
      <div className="field-row">
        <SchemaTextField
          name={`${prefix}.vehicle_brand`}
          property={properties.vehicle_brand}
          forceOptional
        />
        <SchemaTextField
          name={`${prefix}.vehicle_model`}
          property={properties.vehicle_model}
          forceOptional
        />
      </div>
      <SchemaTextField
        name={`${prefix}.vehicle_registration_number`}
        property={properties.vehicle_registration_number}
        forceOptional
      />
    </div>
  );
}