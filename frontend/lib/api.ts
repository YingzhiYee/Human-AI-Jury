import type { DemoRunRequest, DemoRunResponse } from "./types";
import { buildMockRunResponse, defaultDemoCase } from "./mockData";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchDefaultCase() {
  return request<DemoRunRequest>("/api/demo/default-case").catch(() => defaultDemoCase);
}

export function runDemo(payload: DemoRunRequest) {
  return request<DemoRunResponse>("/api/demo/run", {
    method: "POST",
    body: JSON.stringify(payload),
  }).catch(() => buildMockRunResponse(payload));
}
