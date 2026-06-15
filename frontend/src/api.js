const API_ROOT = new URL("api/", window.location.href).toString().replace(/\/$/, "");

async function request(path, options = {}) {
  const url = `${API_ROOT}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) {
    let detail = `请求失败: ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function fetchStatus() {
  return request("/status");
}

export function fetchRepos(params = {}) {
  const qs = new URLSearchParams();
  if (params.project) qs.set("project", params.project);
  if (params.path) qs.set("path", params.path);
  const q = qs.toString();
  return request(`/repos${q ? `?${q}` : ""}`);
}

export function fetchSubscribedRepos(params = {}) {
  const qs = new URLSearchParams();
  if (params.project) qs.set("project", params.project);
  if (params.path) qs.set("path", params.path);
  const q = qs.toString();
  return request(`/repos/subscribed${q ? `?${q}` : ""}`);
}

export function fetchMe() {
  return request("/user/me");
}

export function subscribeRepo(repoKey) {
  return request("/subscriptions", {
    method: "POST",
    body: JSON.stringify({ repo_key: repoKey }),
  });
}

export function unsubscribeRepo(repoKey) {
  return request(`/subscriptions/${encodeURIComponent(repoKey)}`, {
    method: "DELETE",
  });
}

export function fetchSettings() {
  return request("/settings");
}

export function saveSettings(emailEnabled) {
  return request("/settings", {
    method: "PUT",
    body: JSON.stringify({ email_enabled: emailEnabled }),
  });
}
