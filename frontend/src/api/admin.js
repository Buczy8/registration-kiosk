import { apiRequest } from "./client.js";

export async function getAdminDashboard({ token, sequenceDate = null }) {
  const params = new URLSearchParams();
  if (sequenceDate) params.set("sequence_date", sequenceDate);

  const query = params.toString();
  const response = await apiRequest(`/admin/dashboard${query ? `?${query}` : ""}`, {
    token,
    contentType: null,
  });
  return response.json();
}

export async function getAdminSystemStatus({ token }) {
  const response = await apiRequest("/admin/dashboard/system-status", {
    token,
    contentType: null,
  });
  return response.json();
}

export async function getAdminUsers({ token, limit = 20, offset = 0 }) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const response = await apiRequest(`/admin/users?${params.toString()}`, {
    token,
    contentType: null,
  });
  return response.json();
}

export async function lockAdminUser({ token, userId, days = 7 }) {
  const params = new URLSearchParams();
  params.set("days", String(days));

  const response = await apiRequest(`/admin/users/${userId}/lock?${params.toString()}`, {
    method: "PATCH",
    token,
    contentType: null,
  });
  return response.json();
}

export async function unlockAdminUser({ token, userId }) {
  const response = await apiRequest(`/admin/users/${userId}/unlock`, {
    method: "PATCH",
    token,
    contentType: null,
  });
  return response.json();
}

export async function deleteAdminUser({ token, userId }) {
  const response = await apiRequest(`/admin/users/${userId}`, {
    method: "DELETE",
    token,
    contentType: null,
  });
  return response.json();
}

export async function getAdminSubmissions({
  token,
  status = null,
  sequenceDate = null,
  mode = null,
  role = null,
  vehicleType = null,
  lastName = null,
  limit = 20,
  offset = 0,
}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (sequenceDate) params.set("sequence_date", sequenceDate);
  if (mode) params.set("mode", mode);
  if (role) params.set("role", role);
  if (vehicleType) params.set("vehicle_type", vehicleType);
  if (lastName) params.set("last_name", lastName);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const response = await apiRequest(`/admin/submissions?${params.toString()}`, {
    token,
    contentType: null,
  });
  return response.json();
}

export async function getAdminSubmissionDetails({ token, submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}`, {
    token,
    contentType: null,
  });
  return response.json();
}

export async function fetchAdminSubmissionPdf({ token, submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}/pdf`, {
    token,
    contentType: null,
  });
  return response.blob();
}

export async function queueSubmissionForPrint({ token, submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}/print`, {
    method: "POST",
    token,
    contentType: null,
  });
  return response.json();
}

export async function getAdminPrintJobs({
  token,
  status = null,
  sequenceDate = null,
  limit = 20,
  offset = 0,
}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (sequenceDate) params.set("sequence_date", sequenceDate);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const response = await apiRequest(`/admin/print-jobs?${params.toString()}`, {
    token,
    contentType: null,
  });
  return response.json();
}

export async function executePrintJob(jobId, token) {
  const response = await apiRequest(`/admin/print-jobs/${jobId}/print`, {
    method: "POST",
    token,
    contentType: null,
  });
  return response.json();
}