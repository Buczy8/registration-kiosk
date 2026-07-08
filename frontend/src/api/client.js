const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const KIOSK_TOKEN = import.meta.env.VITE_KIOSK_TOKEN || "";

let onUnauthorized = null;

export function setUnauthorizedHandler(handler) {
  onUnauthorized = typeof handler === "function" ? handler : null;
}

async function parseApiError(response) {
  let message = `Wystąpił błąd API (HTTP ${response.status})`;

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
      message = data.detail;
    }
  } catch {
    // Ignorujemy błędy parsowania odpowiedzi
  }

  const error = new Error(message);
  error.status = response.status;
  return error;
}

function buildHeaders({ token, contentType }) {
  const headers = {
    "X-Kiosk-Token": KIOSK_TOKEN,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  return headers;
}

export async function apiRequest(path, options = {}) {
  const {
    method = "GET",
    body,
    token = null,
    contentType = "application/json",
    credentials = "include",
  } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials,
    headers: buildHeaders({ token, contentType }),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await parseApiError(response);
    if (response.status === 401 && onUnauthorized) {
      onUnauthorized();
    }
    throw error;
  }

  return response;
}

