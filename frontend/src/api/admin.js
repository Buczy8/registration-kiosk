import { apiRequest } from "./client.js";

export async function getAdminDashboard({ sequenceDate = null }) {
  const params = new URLSearchParams();
  if (sequenceDate) params.set("sequence_date", sequenceDate);

  const query = params.toString();
  const response = await apiRequest(`/admin/dashboard${query ? `?${query}` : ""}`, {
    contentType: null,
  });
  return response.json();
}

export async function getAdminSystemStatus() {
  const response = await apiRequest("/admin/dashboard/system-status", {
    contentType: null,
  });
  return response.json();
}

export async function getAdminUsers({ limit = 20, offset = 0 }) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const response = await apiRequest(`/admin/users?${params.toString()}`, {
    contentType: null,
  });
  return response.json();
}

export async function lockAdminUser({ userId, days = 7 }) {
  const params = new URLSearchParams();
  params.set("days", String(days));

  const response = await apiRequest(`/admin/users/${userId}/lock?${params.toString()}`, {
    method: "PATCH",
    contentType: null,
  });
  return response.json();
}

export async function unlockAdminUser({ userId }) {
  const response = await apiRequest(`/admin/users/${userId}/unlock`, {
    method: "PATCH",
    contentType: null,
  });
  return response.json();
}

export async function deleteAdminUser({ userId }) {
  const response = await apiRequest(`/admin/users/${userId}`, {
    method: "DELETE",
    contentType: null,
  });
  return response.json();
}

export async function getAdminSubmissions({
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
    contentType: null,
  });
  return response.json();
}

export async function getAdminSubmissionDetails({ submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}`, {
    contentType: null,
  });
  return response.json();
}

export async function fetchAdminSubmissionPdf({ submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}/pdf`, {
    contentType: null,
  });
  return response.blob();
}

export async function queueSubmissionForPrint({ submissionId }) {
  const response = await apiRequest(`/admin/submissions/${submissionId}/print`, {
    method: "POST",
    contentType: null,
  });
  return response.json();
}

export async function getAdminPrintJobs({
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
    contentType: null,
  });
  return response.json();
}

export async function executePrintJob(jobId) {
  const response = await apiRequest(`/admin/print-jobs/${jobId}/print`, {
    method: "POST",
    contentType: null,
  });
  return response.json();
}