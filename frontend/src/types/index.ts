/**
 * Frontend TypeScript Data Models matching Backend Pydantic Schemas
 */

export type SubmissionStatus =
  | 'QUEUED'
  | 'COMPILING'
  | 'RUNNING'
  | 'ACCEPTED'
  | 'WRONG_ANSWER'
  | 'TIME_LIMIT_EXCEEDED'
  | 'MEMORY_LIMIT_EXCEEDED'
  | 'OUTPUT_LIMIT_EXCEEDED'
  | 'COMPILATION_ERROR'
  | 'RUNTIME_ERROR'
  | 'SYSTEM_ERROR';

export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface TestCaseSample {
  id: number;
  input: string;
  expected_output: string;
}

export interface ProblemListItem {
  id: number;
  title: string;
  description: string;
  input_description?: string | null;
  output_description?: string | null;
  difficulty: string;
  tags?: string | null;
  time_limit_ms: number;
  memory_limit_mb: number;
  created_at: string;
}

export interface ProblemDetail extends ProblemListItem {
  sample_testcases: TestCaseSample[];
}

export interface TestCaseResultSummary {
  testcase_index: number;
  status: SubmissionStatus;
  duration_ms: number;
}

export interface SubmissionResponse {
  id: string;
  problem_id: number;
  language: string;
  status: SubmissionStatus;
  execution_time_ms?: number | null;
  memory_used_mb?: number | null;
  error_message?: string | null;
  testcase_results?: TestCaseResultSummary[] | null;
  created_at: string;
  completed_at?: string | null;
}

export interface SubmissionListResponse {
  submissions: SubmissionResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  redis: boolean;
}
