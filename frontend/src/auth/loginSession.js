const STORAGE_KEY = "video_search_ui_logged_in";
const EMAIL_KEY = "video_search_ui_email";
const TOKEN_KEY = "video_search_ui_access_token";

export function isLoggedIn() {
  try {
    return (
      sessionStorage.getItem(STORAGE_KEY) === "1" &&
      sessionStorage.getItem(EMAIL_KEY) !== null &&
      !!sessionStorage.getItem(TOKEN_KEY)
    );
  } catch {
    return false;
  }
}

export function getLoggedInEmail() {
  try {
    return sessionStorage.getItem(EMAIL_KEY) || "";
  } catch {
    return "";
  }
}

export function getAccessToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setLoggedIn(email, accessToken) {
  sessionStorage.setItem(STORAGE_KEY, "1");
  sessionStorage.setItem(EMAIL_KEY, String(email ?? ""));
  if (accessToken) {
    sessionStorage.setItem(TOKEN_KEY, String(accessToken));
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function logout() {
  sessionStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(EMAIL_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}
