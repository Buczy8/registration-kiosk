import { useCallback, useMemo } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  GUARDIAN_FIELDS,
  IdentityDocumentType,
  ParticipantRole,
  buildAccountSubmission,
  buildGuestSubmissions,
  createDefaultFormValues,
  createEmptyMinor,
} from "../lib/registrationFormShared.js";
import { buildFormSchema } from "../lib/registrationSchemas.js";

export function useRegistrationForm({ schemaJson, mode, role, vehicleType }) {
  const schema = useMemo(() => schemaJson || {}, [schemaJson]);
  const properties = schema.properties || {};
  const requireRoleSelection = mode === "guest";

  const formSchema = useMemo(
    () => buildFormSchema({ schemaJson: schema, requireRoleSelection }),
    [schema, requireRoleSelection],
  );

  const methods = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: createDefaultFormValues({ mode, role, vehicleType }),
  });

  const { control, setValue, getValues } = methods;
  const participantRole = useWatch({ control, name: "participantRole" });

  const handleIdentityDocumentTypeChange = useCallback(
    (value) => {
      setValue("identityDocumentType", value, { shouldDirty: true, shouldValidate: true });
      if (value === IdentityDocumentType.PESEL) {
        setValue("payload.id_card_series", "", { shouldDirty: true });
        setValue("payload.id_card_number", "", { shouldDirty: true });
        return;
      }
      setValue("payload.pesel", "", { shouldDirty: true });
    },
    [setValue],
  );

  const handleParticipantRoleChange = useCallback(
    (value) => {
      setValue("participantRole", value, { shouldDirty: true, shouldValidate: true });

      if (value === ParticipantRole.LEGAL_GUARDIAN) {
        setValue("minors", [createEmptyMinor()], { shouldDirty: true });
      } else {
        setValue("minors", [], { shouldDirty: true });
        const payload = { ...getValues("payload") };
        for (const fieldName of GUARDIAN_FIELDS) {
          delete payload[fieldName];
        }
        setValue("payload", payload, { shouldDirty: true });
      }
    },
    [getValues, setValue],
  );

  const buildSubmissions = useCallback(
    (data) => {
      if (mode === "guest") {
        return buildGuestSubmissions(data, schema);
      }
      return [buildAccountSubmission(data, schema, role, vehicleType)];
    },
    [mode, role, schema, vehicleType],
  );

  return {
    methods,
    schema,
    properties,
    participantRole: participantRole || getValues("participantRole"),
    handleIdentityDocumentTypeChange,
    handleParticipantRoleChange,
    buildSubmissions,
  };
}
