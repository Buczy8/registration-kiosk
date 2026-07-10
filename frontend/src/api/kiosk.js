import { apiRequest } from "./client.js";

export async function getActiveForm() {
  const response = await apiRequest("/kiosk/forms/active", {
    contentType: null,
  });
  return response.json();
}

export async function createGuestSubmission(payload) {
  const response = await apiRequest("/kiosk/submissions", {
    method: "POST",
    credentials: "omit",
    body: payload,
  });
  return response.json();
}

export async function fetchSubmissionPdfBlob(submissionId) {
  const response = await apiRequest(`/kiosk/submissions/${submissionId}/pdf`, {
    contentType: null,
  });
  return response.blob();
}

export async function createAccountSubmission(payload) {
  const response = await apiRequest("/kiosk/submissions", {
    method: "POST",
    body: payload,
  });
  return response.json();
}