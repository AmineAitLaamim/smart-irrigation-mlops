const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include", // sends httpOnly cookie automatically
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (res.status === 401 && !isRetry) {
    // Attempt token refresh via our Next.js route handler (one attempt only)
    const refresh = await fetch("/api/auth/refresh", { method: "POST" });
    if (!refresh.ok) {
      if (typeof window !== 'undefined') {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
    // Retry original request (mark as retry to prevent infinite loop)
    return request<T>(path, options, true);
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  if (res.status === 204) {
    return {} as T;
  }
  
  return res.json();
}

export const api = {
  get:    <T>(path: string) => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown) => request<T>(path, { method: "PUT",  body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
