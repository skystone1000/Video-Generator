const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export function assetVideoUrl(assetId: number): string {
  return `${API_BASE}/api/assets/${assetId}/video`;
}

export function assetThumbnailUrl(assetId: number): string {
  return `${API_BASE}/api/assets/${assetId}/thumbnail`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep HTTP status fallback.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body)
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body)
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" })
};
