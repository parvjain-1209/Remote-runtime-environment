import React, { useEffect, useRef, useState } from 'react';
import { CodeEditor } from '../components/CodeEditor';
import { StatusBadge } from '../components/StatusBadge';
import {
  fetchProblemDetail,
  isTerminalStatus,
  pollSubmission,
  submitCode,
} from '../services/api';
import { ProblemDetail, SubmissionResponse } from '../types';

interface ProblemWorkspaceProps {
  problemId: number;
  onBack: () => void;
}

const DEFAULT_STARTER_TEMPLATE = `#include <iostream>
using namespace std;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int a, b;
    if (cin >> a >> b) {
        cout << a + b << "\\n";
    }

    return 0;
}
`;

export const ProblemWorkspace: React.FC<ProblemWorkspaceProps> = ({
  problemId,
  onBack,
}) => {
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loadingProblem, setLoadingProblem] = useState<boolean>(true);
  const [problemError, setProblemError] = useState<string | null>(null);

  const [sourceCode, setSourceCode] = useState<string>(DEFAULT_STARTER_TEMPLATE);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [activeSubmission, setActiveSubmission] = useState<SubmissionResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const pollCleanupRef = useRef<(() => void) | null>(null);

  // Clean up polling loop when unmounted
  useEffect(() => {
    return () => {
      if (pollCleanupRef.current) {
        pollCleanupRef.current();
      }
    };
  }, []);

  const loadProblem = async () => {
    setLoadingProblem(true);
    setProblemError(null);
    try {
      const data = await fetchProblemDetail(problemId);
      setProblem(data);
    } catch (err: any) {
      setProblemError(err.message || 'Failed to load problem details.');
    } finally {
      setLoadingProblem(false);
    }
  };

  useEffect(() => {
    loadProblem();
  }, [problemId]);

  const handleSubmit = async () => {
    if (!sourceCode.trim() || submitting) return;

    // Clear previous poll loop if active
    if (pollCleanupRef.current) {
      pollCleanupRef.current();
      pollCleanupRef.current = null;
    }

    setSubmitting(true);
    setSubmitError(null);
    setActiveSubmission(null);

    try {
      const initialSub = await submitCode(problemId, sourceCode, 'cpp');
      setActiveSubmission(initialSub);

      if (isTerminalStatus(initialSub.status)) {
        setSubmitting(false);
        return;
      }

      // Start live polling loop
      const cleanup = pollSubmission(
        initialSub.id,
        (updatedSub) => {
          setActiveSubmission(updatedSub);
          if (isTerminalStatus(updatedSub.status)) {
            setSubmitting(false);
          }
        },
        (err) => {
          setSubmitError(`Polling update error: ${err.message}`);
          setSubmitting(false);
        }
      );

      pollCleanupRef.current = cleanup;
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create submission.');
      setSubmitting(false);
    }
  };

  if (loadingProblem) {
    return (
      <div style={{ padding: '4rem', textAlign: 'center', color: '#94a3b8' }}>
        <div className="pulse-spinner" style={{ width: '28px', height: '28px', margin: '0 auto 1rem auto' }}></div>
        Loading problem details...
      </div>
    );
  }

  if (problemError || !problem) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '600px', margin: '2rem auto' }}>
        <div className="error-box">{problemError || 'Problem not found'}</div>
        <button className="btn-secondary" onClick={onBack}>← Back to Problems</button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'calc(100vh - 120px)' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn-secondary" onClick={onBack} style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}>
            ← Problems
          </button>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            #{problem.id}. {problem.title}
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Time Limit: <strong style={{ color: '#38bdf8' }}>{problem.time_limit_ms} ms</strong></span>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Memory Limit: <strong style={{ color: '#38bdf8' }}>{problem.memory_limit_mb} MB</strong></span>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <span className="pulse-spinner"></span>
                Submitting & Judging...
              </>
            ) : (
              <>
                <span>▶</span> Submit Solution
              </>
            )}
          </button>
        </div>
      </div>

      {/* Split Workspace Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', flex: 1, overflow: 'hidden' }}>
        {/* Left Panel: Problem Statement & Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>Description</h3>
            <p style={{ color: '#cbd5e1', fontSize: '0.9rem', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
              {problem.description}
            </p>
          </div>

          {problem.input_description && (
            <div className="card">
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>Input Format</h4>
              <p style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{problem.input_description}</p>
            </div>
          )}

          {problem.output_description && (
            <div className="card">
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>Output Format</h4>
              <p style={{ color: '#cbd5e1', fontSize: '0.875rem' }}>{problem.output_description}</p>
            </div>
          )}

          {/* Sample Testcases */}
          {problem.sample_testcases && problem.sample_testcases.length > 0 && (
            <div className="card">
              <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
                Sample Testcases
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {problem.sample_testcases.map((tc, index) => (
                  <div key={tc.id || index} style={{ border: '1px solid #1e293b', borderRadius: '8px', padding: '0.75rem', backgroundColor: '#090d16' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', marginBottom: '0.5rem' }}>Sample #{index + 1}</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                      <div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>INPUT</div>
                        <div className="sample-box">{tc.input}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>EXPECTED OUTPUT</div>
                        <div className="sample-box">{tc.expected_output}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submission Error Alert */}
          {submitError && (
            <div className="error-box">
              <strong>Submission Error:</strong> {submitError}
            </div>
          )}

          {/* Active Submission Verdict Panel */}
          {activeSubmission && (
            <div className="card" style={{ border: '1px solid #334155', backgroundColor: '#0f172a' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#94a3b8' }}>Verdict:</span>
                  <StatusBadge status={activeSubmission.status} />
                </div>
                <span style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>
                  ID: {activeSubmission.id.slice(0, 8)}...
                </span>
              </div>

              {/* Metrics Header */}
              {activeSubmission.execution_time_ms !== null && activeSubmission.execution_time_ms !== undefined && (
                <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                  <div>Total Duration: <strong style={{ color: '#38bdf8' }}>{activeSubmission.execution_time_ms} ms</strong></div>
                </div>
              )}

              {/* Sanitized Error Message Box */}
              {activeSubmission.error_message && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f87171', marginBottom: '0.35rem' }}>Compiler / Error Message:</div>
                  <div className="error-box" style={{ fontSize: '0.8rem', maxHeight: '180px', overflowY: 'auto' }}>
                    {activeSubmission.error_message}
                  </div>
                </div>
              )}

              {/* Per-Testcase Breakdown Matrix */}
              {activeSubmission.testcase_results && activeSubmission.testcase_results.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>Testcase Results Summary</div>
                  <table className="data-table" style={{ borderRadius: '6px', overflow: 'hidden' }}>
                    <thead>
                      <tr>
                        <th>Testcase</th>
                        <th>Verdict</th>
                        <th>Execution Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeSubmission.testcase_results.map((tc) => (
                        <tr key={tc.testcase_index}>
                          <td style={{ fontWeight: 600, color: '#cbd5e1' }}>Test Case #{tc.testcase_index + 1}</td>
                          <td><StatusBadge status={tc.status} /></td>
                          <td style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{tc.duration_ms} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel: Interactive Code Editor */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <CodeEditor
            value={sourceCode}
            onChange={setSourceCode}
            disabled={submitting}
            onResetTemplate={() => setSourceCode(DEFAULT_STARTER_TEMPLATE)}
          />
        </div>
      </div>
    </div>
  );
};
