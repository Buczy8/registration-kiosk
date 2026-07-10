import { apiRequest } from "./client.js";

/**
 * Get list of related persons (dependents) for current guardian
 * @param {string} token - JWT auth token
 * @returns {Promise<Array>} List of related persons with optional last_form_preview
 */
export async function listRelatedPersons() {
  const response = await apiRequest("/account/related-persons", {
    contentType: null,
  });
  return response.json();
}

/**
 * Create a new related person (dependent)
 * @param {string} token - JWT auth token
 * @param {Object} data - Related person data
 * @param {string} data.first_name - First name
 * @param {string} data.last_name - Last name
 * @param {string|null} data.birth_date - Birth date (ISO 8601, optional)
 * @returns {Promise<Object>} Created related person
 */
export async function createRelatedPerson(data) {
  const response = await apiRequest("/account/related-persons", {
    method: "POST",
    body: data,
  });
  return response.json();
}

/**
 * Get a specific related person by ID
 * @param {string} relatedPersonId - UUID of the related person
 * @returns {Promise<Object>} Related person data
 */
export async function getRelatedPerson(relatedPersonId) {
  const response = await apiRequest(`/account/related-persons/${relatedPersonId}`, {
    contentType: null,
  });
  return response.json();
}

/**
 * Get the last form preview for a related person
 * @param {string} relatedPersonId - UUID of the related person
 * @returns {Promise<Object|null>} FormPreview snapshot or null if no submissions
 */
export async function getFormPreview(relatedPersonId) {
  const response = await apiRequest(
    `/account/related-persons/${relatedPersonId}/form-preview`,
    {
      contentType: null,
    }
  );
  return response.json();
}

/**
 * Create a submission for a related person (dependent)
 * Does NOT update the guardian's profile
 * @param {string} token - JWT auth token
 * @param {string} relatedPersonId - UUID of the related person
 * @param {Object} payload - Submission data (same as account submission)
 * @returns {Promise<Object>} Created submission response
 */
export async function createSubmissionForRelatedPerson(relatedPersonId, payload) {
  const url = new URL(`${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/account/submissions/for-related-person`, window.location.origin);
  url.searchParams.append("related_person_id", relatedPersonId);

  const headers = {
    "X-Kiosk-Token": import.meta.env.VITE_KIOSK_TOKEN || "",
    "Content-Type": "application/json",
  };

  const response = await fetch(url.toString(), {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Błąd przy wysyłaniu formularza (HTTP ${response.status})`;
    try {
      const data = await response.json();
      if (Array.isArray(data?.error?.details)) {
        message = data.error.details
          .map((item) => {
            const path = Array.isArray(item.loc) ? item.loc.join(".") : item.loc;
            return `${path}: ${item.msg}`;
          })
          .join("; ");
      } else if (data?.error?.message) {
        message = data.error.message;
      } else if (Array.isArray(data?.detail)) {
        message = data.detail
          .map((item) => {
            const path = Array.isArray(item.loc) ? item.loc.join(".") : item.loc;
            return `${path}: ${item.msg}`;
          })
          .join("; ");
      } else if (data?.detail) {
        message = String(data.detail);
      }
    } catch {
      // Ignorujemy błędy parsowania odpowiedzi
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return response.json();
}
