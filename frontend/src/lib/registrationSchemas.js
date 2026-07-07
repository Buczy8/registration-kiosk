import { z } from "zod";
import {
  GUARDIAN_FIELDS,
  SIGNATURE_PLACE_FIELD,
  VEHICLE_DATA_FIELDS,
} from "./registrationFormShared.js";

const minorSchema = z.object({
  id: z.string().optional(),
  guardian_relation: z.string().trim().min(1, "Wybierz typ opiekuna."),
  minor_first_name: z.string().trim().min(1, "Podaj imię podopiecznego."),
  minor_last_name: z.string().trim().min(1, "Podaj nazwisko podopiecznego."),
  vehicle_type: z.string().trim().min(1),
  vehicle_brand: z.string().optional().default(""),
  vehicle_model: z.string().optional().default(""),
  vehicle_registration_number: z.string().optional().default(""),
});

function requiredFieldErrors(schemaJson, payload) {
  const requiredFields = schemaJson?.required || [];
  const fieldTitles = schemaJson?.properties || {};
  const errors = [];

  for (const field of requiredFields) {
    if (GUARDIAN_FIELDS.includes(field) || VEHICLE_DATA_FIELDS.includes(field)) {
      continue;
    }
    if (!payload[field]?.trim()) {
      const title = fieldTitles[field]?.title || field;
      errors.push(`Pole wymagane: ${title}.`);
    }
  }

  return errors;
}

export function buildFormSchema({ schemaJson, requireRoleSelection = true }) {
  return z
    .object({
      participantRole: requireRoleSelection
        ? z.string().trim().min(1, "Wybierz rolę uczestnika.")
        : z.string().trim().optional(),
      vehicleType: z.string().trim().optional(),
      identityDocumentType: z.enum(["pesel", "id_card"]),
      payload: z.record(z.string(), z.string().optional()),
      declarationsReviewed: z.boolean(),
      signatureImageBase64: z.string().trim().optional(),
      minors: z.array(minorSchema).optional(),
    })
    .superRefine((data, ctx) => {
      const fieldErrors = requiredFieldErrors(schemaJson, data.payload);
      fieldErrors.forEach((message) => {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message,
        });
      });

      if (requireRoleSelection && data.participantRole !== "legal_guardian" && !data.vehicleType) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Wybierz typ pojazdu.",
        });
      }

      if (schemaJson?.identity_document_rule === "pesel_or_id_card") {
        if (data.identityDocumentType === "pesel") {
          const pesel = data.payload.pesel?.trim() || "";
          if (!pesel) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Podaj PESEL.",
            });
          } else if (!/^\d{11}$/.test(pesel)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "PESEL musi mieć 11 cyfr.",
            });
          }
        } else {
          const hasSeries = Boolean(data.payload.id_card_series?.trim());
          const hasNumber = Boolean(data.payload.id_card_number?.trim());
          if (!hasSeries || !hasNumber) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Podaj serię i numer dowodu osobistego.",
            });
          }
        }
      }

      if (data.participantRole === "legal_guardian") {
        const minors = data.minors || [];
        if (minors.length === 0) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Dodaj co najmniej jednego podopiecznego.",
          });
        }
      }

      if (!data.declarationsReviewed) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Przewiń i zapoznaj się z oświadczeniami oraz akceptacją ryzyka.",
        });
      }

      if (!data.payload[SIGNATURE_PLACE_FIELD]?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Podaj datę i miejscowość.",
        });
      }

      if (!data.signatureImageBase64) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Złóż podpis w polu podpisu.",
        });
      }
    });
}

export function flattenZodErrors(result) {
  if (result.success) {
    return [];
  }
  return result.error.issues.map((issue) => issue.message);
}

