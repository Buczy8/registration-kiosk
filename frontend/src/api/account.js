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
  const response = await apiRequest(
    `/account/submissions/for-related-person?related_person_id=${relatedPersonId}`,
    {
      method: "POST",
      body: payload,
    }
  );
  return response.json();
}
