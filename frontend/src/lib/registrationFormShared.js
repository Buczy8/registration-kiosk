export const ParticipantRole = {
  DRIVER: "driver",
  PASSENGER: "passenger",
  LEGAL_GUARDIAN: "legal_guardian",
};

export const VehicleType = {
  CAR: "car",
  MOTORCYCLE: "motorcycle",
  GOKART: "gokart",
};

export const IdentityDocumentType = {
  PESEL: "pesel",
  ID_CARD: "id_card",
};

export const GuardianRelation = {
  PARENT: "parent",
  GUARDIAN: "guardian",
  AUTHORIZED_PERSON: "authorized_person",
};

export const PARTICIPANT_ROLES = [
  { value: ParticipantRole.DRIVER, label: "Kierowca" },
  { value: ParticipantRole.PASSENGER, label: "Pasażer" },
  { value: ParticipantRole.LEGAL_GUARDIAN, label: "Opiekun prawny" },
];

export const VEHICLE_TYPES = [
  { value: VehicleType.CAR, label: "Samochód" },
  { value: VehicleType.MOTORCYCLE, label: "Motocykl" },
  { value: VehicleType.GOKART, label: "Gokart" },
];

export function labelForRole(value) {
  return PARTICIPANT_ROLES.find((role) => role.value === value)?.label ?? value;
}

export function labelForVehicle(value) {
  return VEHICLE_TYPES.find((vehicle) => vehicle.value === value)?.label ?? value;
}

export const IDENTITY_DOCUMENT_TYPES = [
  { value: IdentityDocumentType.PESEL, label: "PESEL" },
  { value: IdentityDocumentType.ID_CARD, label: "Dowód osobisty (seria i numer)" },
];

export const IDENTITY_FIELDS = ["pesel", "id_card_series", "id_card_number"];
export const GUARDIAN_FIELDS = ["guardian_relation", "minor_first_name", "minor_last_name"];
export const VEHICLE_DATA_FIELDS = [
  "vehicle_brand",
  "vehicle_model",
  "vehicle_registration_number",
];
export const PERSONAL_DATA_FIELDS = [
  "first_name",
  "last_name",
  "residence_address",
  "birth_date",
  "phone",
  "email",
  "emergency_contact_name",
  "emergency_contact_phone",
];
export const GUARDIAN_RELATIONS = [
  { value: GuardianRelation.PARENT, label: "Rodzic" },
  { value: GuardianRelation.GUARDIAN, label: "Opiekun prawny" },
  { value: GuardianRelation.AUTHORIZED_PERSON, label: "Osoba upoważniona" },
];
export const SIGNATURE_PLACE_FIELD = "signature_place";

export function getDefaultSignaturePlace() {
  const today = new Date().toLocaleDateString("pl-PL");
  return `Biłgoraj, ${today}`;
}

export function createEmptyMinor() {
  return {
    id: crypto.randomUUID(),
    guardian_relation: "",
    minor_first_name: "",
    minor_last_name: "",
    vehicle_type: VehicleType.CAR,
    vehicle_brand: "",
    vehicle_model: "",
    vehicle_registration_number: "",
  };
}

export function createDefaultFormValues({ mode, role, vehicleType } = {}) {
  if (mode === "account") {
    return {
      participantRole: role || ParticipantRole.DRIVER,
      vehicleType: vehicleType || VehicleType.CAR,
      identityDocumentType: IdentityDocumentType.PESEL,
      payload: {},
      declarationsReviewed: false,
      signatureImageBase64: "",
      minors: [],
      consents: { image_publication: false },
    };
  }

  return {
    participantRole: ParticipantRole.DRIVER,
    vehicleType: VehicleType.CAR,
    identityDocumentType: IdentityDocumentType.PESEL,
    payload: {
      [SIGNATURE_PLACE_FIELD]: getDefaultSignaturePlace(),
    },
    declarationsReviewed: false,
    signatureImageBase64: "",
    minors: [],
    consents: { image_publication: false },
  };
}

export function getInputType(property) {
  if (property.format === "date") {
    return "date";
  }
  if (property.format === "email") {
    return "email";
  }
  return "text";
}

export function isIdentityField(fieldName) {
  return IDENTITY_FIELDS.includes(fieldName);
}

export function isGuardianField(fieldName) {
  return GUARDIAN_FIELDS.includes(fieldName);
}

export function isVehicleField(fieldName) {
  return VEHICLE_DATA_FIELDS.includes(fieldName);
}

export function getRoleLabel(role) {
  return PARTICIPANT_ROLES.find((item) => item.value === role)?.label ?? role;
}

export function getVehicleLabel(vehicleType) {
  return VEHICLE_TYPES.find((item) => item.value === vehicleType)?.label ?? vehicleType;
}

export function mapPrefillToFormData(prefill) {
  const formData = {
    [SIGNATURE_PLACE_FIELD]: getDefaultSignaturePlace(),
  };

  if (!prefill) {
    return formData;
  }

  if (prefill.first_name) formData.first_name = prefill.first_name;
  if (prefill.last_name) formData.last_name = prefill.last_name;
  if (prefill.email) formData.email = prefill.email;
  if (prefill.phone) formData.phone = prefill.phone;
  if (prefill.address) formData.residence_address = prefill.address;
  if (prefill.birth_date) formData.birth_date = prefill.birth_date;
  if (prefill.ice_name) formData.emergency_contact_name = prefill.ice_name;
  if (prefill.ice_phone) formData.emergency_contact_phone = prefill.ice_phone;

  if (prefill.pesel) {
    formData.pesel = prefill.pesel;
  }
  if (prefill.id_card_series) {
    formData.id_card_series = prefill.id_card_series;
  }
  if (prefill.id_card_number) {
    formData.id_card_number = prefill.id_card_number;
  }

  if (
    !formData.pesel &&
    !formData.id_card_series &&
    !formData.id_card_number &&
    prefill.document_number
  ) {
    const documentNumber = prefill.document_number.trim();
    if (/^\d{11}$/.test(documentNumber)) {
      formData.pesel = documentNumber;
    } else {
      formData.id_card_number = documentNumber;
    }
  }

  if (prefill.vehicle) {
    const brandModel = prefill.vehicle.brand_model?.trim() || "";
    const spaceIndex = brandModel.indexOf(" ");
    if (spaceIndex > 0) {
      formData.vehicle_brand = brandModel.slice(0, spaceIndex);
      formData.vehicle_model = brandModel.slice(spaceIndex + 1);
    } else if (brandModel) {
      formData.vehicle_brand = brandModel;
    }
    if (prefill.vehicle.registration_number) {
      formData.vehicle_registration_number = prefill.vehicle.registration_number;
    }
  }

  return formData;
}

export function inferIdentityDocumentType(formData) {
  if (formData.pesel) {
    return IdentityDocumentType.PESEL;
  }
  if (formData.id_card_series || formData.id_card_number) {
    return IdentityDocumentType.ID_CARD;
  }
  return IdentityDocumentType.PESEL;
}

export function buildPayloadJson(
  formData,
  schema,
  identityDocumentType,
  { excludeVehicleFields = false } = {},
) {
  const payload = {};
  const properties = schema.properties || {};

  for (const fieldName of Object.keys(properties)) {
    if (isGuardianField(fieldName)) {
      continue;
    }
    if (excludeVehicleFields && isVehicleField(fieldName)) {
      continue;
    }
    if (isIdentityField(fieldName)) {
      if (identityDocumentType === IdentityDocumentType.PESEL && fieldName !== "pesel") {
        continue;
      }
      if (identityDocumentType === IdentityDocumentType.ID_CARD && fieldName === "pesel") {
        continue;
      }
    }
    const value = formData[fieldName]?.trim();
    if (value) {
      payload[fieldName] = value;
    }
  }

  if (!excludeVehicleFields) {
    applyVehicleFields(payload, formData);
  }

  payload[SIGNATURE_PLACE_FIELD] = formData[SIGNATURE_PLACE_FIELD]?.trim() || "";

  return payload;
}

export function applyVehicleFields(payload, source) {
  for (const fieldName of VEHICLE_DATA_FIELDS) {
    payload[fieldName] = source[fieldName]?.trim() || "";
  }
  return payload;
}

export function buildSubmissionPayload({
  basePayload,
  minor,
  participantRole,
  vehicleType,
  consents = { image_publication: false },
  signatureImageBase64,
}) {
  const payloadJson = { ...basePayload };
  if (participantRole === ParticipantRole.LEGAL_GUARDIAN && minor) {
    payloadJson.guardian_relation = minor.guardian_relation;
    payloadJson.minor_first_name = minor.minor_first_name.trim();
    payloadJson.minor_last_name = minor.minor_last_name.trim();
    applyVehicleFields(payloadJson, minor);
  }

  return {
    participant_role: participantRole,
    vehicle_type: minor?.vehicle_type ?? vehicleType,
    payload_json: payloadJson,
    consents_json: {
      image_publication: consents.image_publication,
    },
    declarations_accepted: true,
    signature_image_base64: signatureImageBase64,
  };
}

export function buildGuestSubmissions(data, schema) {
  const basePayload = buildPayloadJson(data.payload, schema, data.identityDocumentType, {
    excludeVehicleFields: data.participantRole === ParticipantRole.LEGAL_GUARDIAN,
  });

  if (data.participantRole === ParticipantRole.LEGAL_GUARDIAN) {
    return data.minors.map((minor) =>
      buildSubmissionPayload({
        basePayload,
        minor,
        participantRole: data.participantRole,
        vehicleType: data.vehicleType,
        consents: data.consents,
        signatureImageBase64: data.signatureImageBase64,
      }),
    );
  }

  return [
    buildSubmissionPayload({
      basePayload,
      participantRole: data.participantRole,
      vehicleType: data.vehicleType,
      consents: data.consents,
      signatureImageBase64: data.signatureImageBase64,
    }),
  ];
}

export function buildAccountSubmission(data, schema, role, vehicleType) {
  const basePayload = buildPayloadJson(data.payload, schema, data.identityDocumentType);
  return buildSubmissionPayload({
    basePayload,
    participantRole: role,
    vehicleType,
    signatureImageBase64: data.signatureImageBase64,
  });
}

export function getNestedError(errors, path) {
  return path.split(".").reduce((current, key) => current?.[key], errors);
}

export function collectFormErrorMessages(errors) {
  if (!errors) {
    return [];
  }

  const messages = [];
  for (const value of Object.values(errors)) {
    if (value?.message) {
      messages.push(value.message);
      continue;
    }
    if (typeof value === "object") {
      messages.push(...collectFormErrorMessages(value));
    }
  }
  return messages;
}
