import { apiRequest } from "./client.js";

function withAuthFriendlyErrors(error) {
  const authError = error;
  switch (authError.status) {
    case 401:
    case 422:
      return new Error("Nieprawidłowy e-mail, hasło lub konto jest zablokowane.");
    case 400:
      return new Error("Rejestracja nie powiodła się. Sprawdź poprawność wprowadzonych danych.");
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

export async function getProfile() {
  const response = await apiRequest("/me/profile", {
    contentType: null,
  });
  return response.json();
}

export async function getFormPrefill(role, vehicleType) {
  const params = new URLSearchParams();
  if (role) params.append("role", role);
  if (vehicleType) params.append("vehicle_type", vehicleType);

  const queryString = params.toString() ? `?${params.toString()}` : "";

  const response = await apiRequest(`/me/form-prefill${queryString}`, {
    contentType: null,
  });
  return response.json();
}