import { apiRequest } from "./client.js";

function withAuthFriendlyErrors(error) {
  const authError = error;
  switch (authError.status) {
    case 401:
    case 422:
      return new Error("Nieprawidłowy adres e-mail lub hasło.");
    case 409:
      return new Error("Konto z podanym adresem e-mail już istnieje.");
    case 423:
      return new Error("Twoje konto zostało tymczasowo zablokowane. Spróbuj ponownie później.");
    default:
      return error;
  }
}

export async function register(payload) {
  try {
    const response = await apiRequest("/auth/register", {
      method: "POST",
      body: payload,
    });
    return response.json();
  } catch (error) {
    throw withAuthFriendlyErrors(error);
  }
}

export async function login(payload) {
  try {
    const response = await apiRequest("/auth/login", {
      method: "POST",
      body: payload,
    });
    return response.json();
  } catch (error) {
    throw withAuthFriendlyErrors(error);
  }
}

export async function logout() {
  await apiRequest("/auth/logout", {
    method: "POST",
    contentType: null,
  });
}

export async function getProfile(token) {
  const response = await apiRequest("/me/profile", {
    token,
    contentType: null,
  });
  return response.json();
}

export async function getFormPrefill(token, role, vehicleType) {
  const params = new URLSearchParams();
  if (role) params.append("role", role);
  if (vehicleType) params.append("vehicle_type", vehicleType);

  const queryString = params.toString() ? `?${params.toString()}` : "";

  const response = await apiRequest(`/me/form-prefill${queryString}`, {
    token,
    contentType: null,
  });
  return response.json();
}