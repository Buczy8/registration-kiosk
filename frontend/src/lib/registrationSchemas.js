import { z } from "zod";
import {
  GUARDIAN_FIELDS,
  IdentityDocumentType,
  ParticipantRole,
  SIGNATURE_PLACE_FIELD,
  VEHICLE_DATA_FIELDS,
} from "./registrationFormShared.js";

const minorDraftSchema = z.object({
  id: z.string().optional(),
  related_person_id: z.string().nullable().optional(),
  guardian_relation: z.string().optional(),
  minor_first_name: z.string().optional(),
  minor_last_name: z.string().optional(),
  vehicle_type: z.string().optional(),
  vehicle_brand: z.string().optional(),
  vehicle_model: z.string().optional(),
  vehicle_registration_number: z.string().optional(),
});

function addMinorFieldIssues(minors, ctx) {
  minors.forEach((minor, index) => {
    if (!minor.guardian_relation?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Wybierz typ opiekuna.",
        path: ["minors", index, "guardian_relation"],
      });
    }
    if (!minor.minor_first_name?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Podaj imię podopiecznego.",
        path: ["minors", index, "minor_first_name"],
      });
    }
    if (!minor.minor_last_name?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Podaj nazwisko podopiecznego.",
        path: ["minors", index, "minor_last_name"],
      });
    }
    if (!minor.vehicle_type?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Wybierz rodzaj pojazdu.",
        path: ["minors", index, "vehicle_type"],
      });
    }
  });
}

function addRequiredFieldIssues(schemaJson, payload, ctx) {
  const requiredFields = schemaJson?.required || [];
  const fieldTitles = schemaJson?.properties || {};

  for (const field of requiredFields) {
    if (GUARDIAN_FIELDS.includes(field) || VEHICLE_DATA_FIELDS.includes(field)) {
      continue;
    }
    if (!payload[field]?.trim()) {
      const title = fieldTitles[field]?.title || field;
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Pole wymagane: ${title}.`,
        path: ["payload", field],
      });
    }
  }
}

export function buildFormSchema({ schemaJson, requireRoleSelection = true }) {
  return z
    .object({
      participantRole: requireRoleSelection
        ? z.string().trim().min(1, "Wybierz rolę uczestnika.")
        : z.string().trim().optional(),
      vehicleType: z.string().trim().optional(),
      identityDocumentType: z.enum([IdentityDocumentType.PESEL, IdentityDocumentType.ID_CARD]),
      payload: z.record(z.string(), z.string().optional()),
      declarationsReviewed: z.boolean(),
      signatureImageBase64: z.string().trim().optional(),
      minors: z.array(minorDraftSchema).optional(),
      consents: z
        .object({
          image_publication: z.boolean().optional(),
        })
        .optional(),
    })
    .superRefine((data, ctx) => {
      addRequiredFieldIssues(schemaJson, data.payload, ctx);

      if (requireRoleSelection && data.participantRole !== ParticipantRole.LEGAL_GUARDIAN && !data.vehicleType) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Wybierz typ pojazdu.",
          path: ["vehicleType"],
        });
      }

      if (schemaJson?.identity_document_rule === "pesel_or_id_card") {
        if (data.identityDocumentType === IdentityDocumentType.PESEL) {
          const pesel = data.payload.pesel?.trim() || "";
          if (!pesel) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Podaj PESEL.",
              path: ["payload", "pesel"],
            });
          } else if (!/^\d{11}$/.test(pesel)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "PESEL musi mieć 11 cyfr.",
              path: ["payload", "pesel"],
            });
          }
        } else {
          const hasSeries = Boolean(data.payload.id_card_series?.trim());
          const hasNumber = Boolean(data.payload.id_card_number?.trim());
          if (!hasSeries) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Podaj serię dowodu osobistego.",
              path: ["payload", "id_card_series"],
            });
          }
          if (!hasNumber) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: "Podaj numer dowodu osobistego.",
              path: ["payload", "id_card_number"],
            });
          }
        }
      }

      if (data.participantRole === ParticipantRole.LEGAL_GUARDIAN) {
        const minors = data.minors || [];
        if (minors.length === 0) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Dodaj co najmniej jednego podopiecznego.",
            path: ["minors"],
          });
        } else {
          addMinorFieldIssues(minors, ctx);
        }
        if (!data.consents?.image_publication) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Zaznacz zgodę na publikację wizerunku podopiecznego.",
            path: ["consents", "image_publication"],
          });
        }
      }

      if (!data.declarationsReviewed) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Przewiń i zapoznaj się z oświadczeniami oraz akceptacją ryzyka.",
          path: ["declarationsReviewed"],
        });
      }

      if (!data.payload[SIGNATURE_PLACE_FIELD]?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Podaj datę i miejscowość.",
          path: ["payload", SIGNATURE_PLACE_FIELD],
        });
      }

      if (!data.signatureImageBase64) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Złóż podpis w polu podpisu.",
          path: ["signatureImageBase64"],
        });
      }
    });
}
