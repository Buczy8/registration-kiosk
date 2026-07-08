export const PARTICIPANT_ROLES = [
  { value: "driver", label: "Kierowca" },
  { value: "passenger", label: "Pasażer" },
  { value: "legal_guardian", label: "Opiekun prawny" },
];

export const VEHICLE_TYPES = [
  { value: "car", label: "Samochód" },
  { value: "motorcycle", label: "Motocykl" },
  { value: "gokart", label: "Gokart" },
];

export function labelForRole(value) {
  return PARTICIPANT_ROLES.find((role) => role.value === value)?.label ?? value;
}

export function labelForVehicle(value) {
  return VEHICLE_TYPES.find((vehicle) => vehicle.value === value)?.label ?? value;
}

export const IDENTITY_DOCUMENT_TYPES = [
  { value: "pesel", label: "PESEL" },
  { value: "id_card", label: "Dowód osobisty (seria i numer)" },
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
  { value: "parent", label: "Rodzic" },
  { value: "guardian", label: "Opiekun prawny" },
  { value: "authorized_person", label: "Osoba upoważniona" },
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
    vehicle_type: "car",
    vehicle_brand: "",
    vehicle_model: "",
    vehicle_registration_number: "",
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
    return "pesel";
  }
  if (formData.id_card_series || formData.id_card_number) {
    return "id_card";
  }
  return "pesel";
}

function validateIdentityDocument(payload, schema, identityDocumentType) {
  if (schema.identity_document_rule !== "pesel_or_id_card") {
    return null;
  }

  if (identityDocumentType === "pesel") {
    if (!payload.pesel?.trim()) {
      return "Podaj PESEL.";
    }
    if (payload.pesel.trim().length !== 11) {
      return "PESEL musi mieć 11 cyfr.";
    }
    return null;
  }

  const hasSeries = Boolean(payload.id_card_series?.trim());
  const hasNumber = Boolean(payload.id_card_number?.trim());
  if (!hasSeries || !hasNumber) {
    return "Podaj serię i numer dowodu osobistego.";
  }

  return null;
}

function validateMinors(minors) {
  const errors = [];

  if (minors.length === 0) {
    errors.push("Dodaj co najmniej jednego podopiecznego.");
    return errors;
  }

  minors.forEach((minor, index) => {
    const label = `Podopieczny ${index + 1}`;
    if (!minor.guardian_relation?.trim()) {
      errors.push(`${label}: wybierz typ opiekuna.`);
    }
    if (!minor.minor_first_name?.trim()) {
      errors.push(`${label}: podaj imię podopiecznego.`);
    }
    if (!minor.minor_last_name?.trim()) {
      errors.push(`${label}: podaj nazwisko podopiecznego.`);
    }
  });

  return errors;
}

export function validateForm({
  schema,
  payload,
  participantRole,
  vehicleType,
  declarationsReviewed,
  identityDocumentType,
  minors = [],
  signatureImageBase64,
  requireRoleSelection = true,
}) {
  const errors = [];

  if (requireRoleSelection && !participantRole) {
    errors.push("Wybierz rolę uczestnika.");
  }
  if (requireRoleSelection && participantRole !== "legal_guardian" && !vehicleType) {
    errors.push("Wybierz typ pojazdu.");
  }

  for (const field of schema.required || []) {
    if (isGuardianField(field) || isVehicleField(field)) {
      continue;
    }
    if (!payload[field]?.trim()) {
      const title = schema.properties?.[field]?.title || field;
      errors.push(`Pole wymagane: ${title}.`);
    }
  }

  const identityError = validateIdentityDocument(payload, schema, identityDocumentType);
  if (identityError) {
    errors.push(identityError);
  }

  if (participantRole === "legal_guardian") {
    errors.push(...validateMinors(minors));
  }

  if (!declarationsReviewed) {
    errors.push("Przewiń i zapoznaj się z oświadczeniami oraz akceptacją ryzyka.");
  }
  if (!payload[SIGNATURE_PLACE_FIELD]?.trim()) {
    errors.push("Podaj datę i miejscowość.");
  }
  if (!signatureImageBase64) {
    errors.push("Złóż podpis w polu podpisu.");
  }

  return errors;
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
      if (identityDocumentType === "pesel" && fieldName !== "pesel") {
        continue;
      }
      if (identityDocumentType === "id_card" && fieldName === "pesel") {
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
  if (participantRole === "legal_guardian" && minor) {
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
