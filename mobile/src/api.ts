/**
 * API client for the PixelForge AI backend.
 * Change API_BASE_URL to your deployed server address.
 */

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:80";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface MeOut {
  id: number;
  email: string;
  plan: string;
}

export interface JobOut {
  id: string;
  status: "queued" | "running" | "done" | "failed";
  image_url: string | null;
  prompt: string;
  created_at: string;
}

export interface GenerateIn {
  prompt: string;
  width?: number;
  height?: number;
  steps?: number;
  guidance?: number;
}

export interface PlanInfo {
  plan: string;
  monthly_limit: number;
  used_this_month: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function signup(email: string, password: string): Promise<void> {
  await request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenOut> {
  return request<TokenOut>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(token: string): Promise<MeOut> {
  return request<MeOut>("/auth/me", {
    headers: authHeaders(token),
  });
}

// ─── Images ───────────────────────────────────────────────────────────────────

export async function generateImage(
  token: string,
  params: GenerateIn
): Promise<JobOut> {
  return request<JobOut>("/images/generate", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(params),
  });
}

export async function pollJob(token: string, jobId: string): Promise<JobOut> {
  return request<JobOut>(`/images/${jobId}`, {
    headers: authHeaders(token),
  });
}

export async function listJobs(token: string): Promise<JobOut[]> {
  return request<JobOut[]>("/images/", {
    headers: authHeaders(token),
  });
}

export async function listPlans(token: string): Promise<PlanInfo> {
  return request<PlanInfo>("/billing/plans", {
    headers: authHeaders(token),
  });
}
