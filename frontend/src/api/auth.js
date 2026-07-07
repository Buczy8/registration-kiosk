const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const KIOSK_TOKEN = import.meta.env.VITE_KIOSK_TOKEN || "";

function authHeaders(token, contentType = "application/json") {
  const headers = {
    "X-Kiosk-Token": KIOSK_TOKEN,
    "Authorization": `Bearer ${token}`,
  };
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  return headers;
}

async function parseAuthError(response) {
  let message = `Wystąpił błąd API (HTTP ${response.status})`;

  try {
    const data = await response.json();
    if (data?.detail) {
      message = data.detail;
    }
  } catch {
    // Ignorujemy błędy parsowania JSON w przypadku braku ciała
  }

  switch (response.status) {
    case 401:
      message = "Nieprawidłowy adres e-mail lub hasło.";
      break;
    case 409:
      message = "Konto z podanym adresem e-mail już istnieje.";
      break;
    case 423:
      message = "Twoje konto zostało tymczasowo zablokowane. Spróbuj ponownie później.";
      break;
  }

  return new Error(message);
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw await parseAuthError(response);
  }
  return response;
}

export async function register(payload) {
  const response = await request("/auth/register", {
    method: "POST",
    headers: {
      "X-Kiosk-Token": KIOSK_TOKEN,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function login(payload) {
  const response = await request("/auth/login", {
    method: "POST",
    headers: {
      "X-Kiosk-Token": KIOSK_TOKEN,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return response.json();
}

export async function getProfile(token) {
  const response = await request("/me/profile", {
    method: "GET",
    headers: authHeaders(token, null),T
  });
  return response.json();
}

export async function getFormPrefill(token, role, vehicleType) {
  const params = new URLSearchParams();
  if (role) params.append("participant_role", role);
  if (vehicleType) params.append("vehicle_type", vehicleType);

  const queryString = params.toString() ? `?${params.toString()}` : "";

  const response = await request(`/me/form-prefill${queryString}`, {
    method: "GET",
    headers: authHeaders(token, null),
  });
  return response.json();
}