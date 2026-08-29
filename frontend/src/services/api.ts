import {
  HealthResponse,
  ProblemDetail,
  ProblemListItem,
  SubmissionListResponse,
  SubmissionResponse,
  SubmissionStatus,
} from '../types';

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';

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
  sourceCode: str,
  language: string = 'cpp'
): Promise<SubmissionResponse> {
  const res = await fetch(`${API_BASE_URL}/submissions/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
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
  const res = await fetch(`${API_BASE_URL}/submissions/${id}`);
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

  const res = await fetch(`${API_BASE_URL}/submissions/?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch submission history (${res.status})`);
  }
  return res.json();
}

export function isTerminalStatus(status: SubmissionStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

/**
 * Polls a submission ID until terminal status is reached or max attempts exceeded.
 * Returns an unbind/cancel function to prevent memory leaks or state updates after unmount.
 */
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
        return; // Terminal state reached or timed out, stop polling loop
      }

      timerId = window.setTimeout(runPoll, intervalMs);
    } catch (err: any) {
      if (isCancelled) return;
      onError(err instanceof Error ? err : new Error(String(err)));
      // Retry poll even on transient network glitch if attempts under max
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
