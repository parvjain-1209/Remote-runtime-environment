import {
  HealthResponse,
  LoginRequest,
  ProblemDetail,
  ProblemListItem,
  RegisterRequest,
  SubmissionListResponse,
  SubmissionResponse,
  SubmissionStatus,
  TokenResponse,
  User,
} from '../types';

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';

const TOKEN_KEY = 'gdg_oj_jwt_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

const TERMINAL_STATUSES: Set<SubmissionStatus> = new Set([
  'ACCEPTED',
  'WRONG_ANSWER',
  'TIME_LIMIT_EXCEEDED',
  'MEMORY_LIMIT_EXCEEDED',
  'OUTPUT_LIMIT_EXCEEDED',
  'COMPILATION_ERROR',
  'RUNTIME_ERROR',
  'SYSTEM_ERROR',
]);

// Auth Endpoints
export async function registerUser(req: RegisterRequest): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Registration failed with status ${res.status}`);
  }

  const data: TokenResponse = await res.json();
  setStoredToken(data.access_token);
  return data;
}

export async function loginUser(req: LoginRequest): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Login failed with status ${res.status}`);
  }

  const data: TokenResponse = await res.json();
  setStoredToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<User> {
  const headers = getAuthHeaders();
  if (!headers.Authorization) {
    throw new Error('No auth token stored');
  }

  const res = await fetch(`${API_BASE_URL}/auth/me`, { headers });
  if (!res.ok) {
    removeStoredToken();
    throw new Error('Session expired or invalid token');
  }

  return res.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchProblems(): Promise<ProblemListItem[]> {
  const res = await fetch(`${API_BASE_URL}/problems/`);
  if (!res.ok) {
    throw new Error(`Failed to fetch problems (${res.status})`);
  }
  return res.json();
}

export async function fetchProblemDetail(id: number): Promise<ProblemDetail> {
  const res = await fetch(`${API_BASE_URL}/problems/${id}`);
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Problem #${id} not found.`);
    }
    throw new Error(`Failed to fetch problem #${id} (${res.status})`);
  }
  return res.json();
}

export async function submitCode(
  problemId: number,
  sourceCode: string,
  language: string = 'cpp'
): Promise<SubmissionResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  };

  const res = await fetch(`${API_BASE_URL}/submissions/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      problem_id: problemId,
      language: language,
      source_code: sourceCode,
    }),
  });

  if (!res.ok) {
    if (res.status === 413) {
      throw new Error('Source code size exceeds 100 KB payload limit.');
    }
    if (res.status === 503) {
      throw new Error('Database service unavailable. Please retry shortly.');
    }
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Submission failed with status ${res.status}`);
  }

  return res.json();
}

export async function fetchSubmission(id: string): Promise<SubmissionResponse> {
  const res = await fetch(`${API_BASE_URL}/submissions/${id}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch submission ${id} (${res.status})`);
  }
  return res.json();
}

export async function fetchSubmissions(
  problemId?: number,
  limit: number = 20,
  offset: number = 0
): Promise<SubmissionListResponse> {
  const params = new URLSearchParams();
  if (problemId !== undefined) {
    params.append('problem_id', problemId.toString());
  }
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const res = await fetch(`${API_BASE_URL}/submissions/?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch submission history (${res.status})`);
  }
  return res.json();
}

export function isTerminalStatus(status: SubmissionStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

export function pollSubmission(
  id: string,
  onUpdate: (sub: SubmissionResponse) => void,
  onError: (err: Error) => void,
  intervalMs: number = 1000,
  maxAttempts: number = 60
): () => void {
  let isCancelled = false;
  let timerId: number | null = null;
  let attempts = 0;

  const runPoll = async () => {
    if (isCancelled) return;
    attempts++;

    try {
      const sub = await fetchSubmission(id);
      if (isCancelled) return;

      onUpdate(sub);

      if (isTerminalStatus(sub.status) || attempts >= maxAttempts) {
        return;
      }

      timerId = window.setTimeout(runPoll, intervalMs);
    } catch (err: any) {
      if (isCancelled) return;
      onError(err instanceof Error ? err : new Error(String(err)));
      if (attempts < maxAttempts) {
        timerId = window.setTimeout(runPoll, intervalMs * 2);
      }
    }
  };

  runPoll();

  return () => {
    isCancelled = true;
    if (timerId !== null) {
      clearTimeout(timerId);
    }
  };
}
