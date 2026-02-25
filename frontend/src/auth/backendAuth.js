import runtimeConfig from "../config/runtimeConfig.js";

export async function loginBackendUser(username, password) {
  await runtimeConfig.load();
  const backendUrl = runtimeConfig.getBackendUrl();
  const controller = new AbortController();
  const timeoutMs = 12000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(`${backendUrl}/auth/login`, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: String(username ?? "").trim(),
        password: String(password ?? ""),
      }),
    });
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error(`Login request timed out after ${timeoutMs}ms.`);
    }
    throw new Error("Login request failed.");
  } finally {
    clearTimeout(timeoutId);
  }
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      errorData?.detail || `Login failed with status ${response.status}`;
    throw new Error(message);
  }
  return response.json();
}
