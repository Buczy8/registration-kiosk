const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const KIOSK_TOKEN = import.meta.env.VITE_KIOSK_TOKEN || "";

function getHeaders(contentType = "application/json") {
  const headers = {
    "X-Kiosk-Token": KIOSK_TOKEN,
  };
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  return headers;
}

async function parseError(response) {
  let message = `HTTP ${response.status}`;
  try {
    const data = await response.json();
    if (data?.error?.message) {
      message = data.error.message;
    }
  } catch {
    // ignore JSON parse errors
  }
  return new Error(message);
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw await parseError(response);
  }
  return response;
}

export async function getActiveForm() {
  const response = await request("/kiosk/forms/active", {
    headers: getHeaders(null),
  });
  return response.json();
}

export async function createGuestSubmission(payload) {
  const response = await request("/kiosk/submissions", {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function downloadSubmissionPdf(submissionId) {
  const response = await request(`/kiosk/submissions/${submissionId}/pdf`, {
    headers: getHeaders(null),
  });
  const blob = await response.blob();
  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
  const filename = filenameMatch?.[1] || `submission-${submissionId}.pdf`;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
