import { Controller, useFormContext } from "react-hook-form";

import {
  PARTICIPANT_ROLES,
  ParticipantRole,
  VEHICLE_TYPES,
} from "../../lib/registrationFormShared.js";
import RadioGroup from "../RadioGroup.jsx";

export default function ParticipantRoleSection({ onParticipantRoleChange }) {
  const { control } = useFormContext();

  return (
    <Controller
      control={control}
      name="participantRole"
      render={({ field: roleField }) => (
        <>
          <RadioGroup
            legend="Rola"
            name="participant_role"
            options={PARTICIPANT_ROLES}
            value={roleField.value}
            onChange={(value) => {
              roleField.onChange(value);
              onParticipantRoleChange(value);
            }}
          />
          {roleField.value !== ParticipantRole.LEGAL_GUARDIAN && (
            <Controller
              control={control}
              name="vehicleType"
              render={({ field: vehicleField }) => (
                <RadioGroup
                  legend="Rodzaj pojazdu"
                  name="vehicle_type"
                  options={VEHICLE_TYPES}
                  value={vehicleField.value}
                  onChange={vehicleField.onChange}
                />
              )}
            />
          )}
        </>
      )}
    />
  );
}
