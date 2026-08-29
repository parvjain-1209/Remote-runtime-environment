import React, { useEffect, useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { fetchSubmissions } from '../services/api';
import { SubmissionResponse } from '../types';

interface SubmissionHistoryProps {
  onSelectProblem?: (problemId: number) => void;
}

export const SubmissionHistory: React.FC<SubmissionHistoryProps> = ({ onSelectProblem }) => {
  const [submissions, setSubmissions] = useState<SubmissionResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [limit] = useState<number>(10);
  const [offset, setOffset] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadSubmissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSubmissions(undefined, limit, offset);
      setSubmissions(data.submissions);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load submission history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubmissions();
  }, [offset, limit]);

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + d.toLocaleDateString();
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }}>Submission History</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Real-time audit log of all participant submissions and container evaluation outcomes.
          </p>
        </div>

        <button className="btn-secondary" onClick={loadSubmissions} disabled={loading}>
          🔄 Refresh
        </button>
      </div>

      {loading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
          <div className="pulse-spinner" style={{ width: '24px', height: '24px', margin: '0 auto 1rem auto' }}></div>
          Loading submission history...
        </div>
      )}

      {error && (
        <div className="error-box" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button className="btn-secondary" onClick={loadSubmissions}>Retry</button>
        </div>
      )}

      {!loading && !error && submissions.length === 0 && (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b', backgroundColor: '#111827', borderRadius: '12px', border: '1px solid #1e293b' }}>
          No submissions found yet. Submit a solution from the problem workspace to see execution results here!
        </div>
      )}

      {!loading && !error && submissions.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Submission ID</th>
                <th>Problem ID</th>
                <th>Language</th>
                <th>Status</th>
                <th>Execution Time</th>
                <th>Submitted At</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => {
                const isExpanded = expandedId === sub.id;
                return (
                  <React.Fragment key={sub.id}>
                    <tr style={{ cursor: 'pointer' }} onClick={() => setExpandedId(isExpanded ? null : sub.id)}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' }}>
                        {sub.id.slice(0, 8)}...
                      </td>
                      <td>
                        <span
                          style={{ color: '#60a5fa', textDecoration: 'underline', cursor: 'pointer' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onSelectProblem) onSelectProblem(sub.problem_id);
                          }}
                        >
                          Problem #{sub.problem_id}
                        </span>
                      </td>
                      <td style={{ textTransform: 'uppercase', fontSize: '0.8rem', color: '#94a3b8' }}>{sub.language}</td>
                      <td><StatusBadge status={sub.status} /></td>
                      <td style={{ fontFamily: 'monospace', color: '#cbd5e1' }}>
                        {sub.execution_time_ms !== null && sub.execution_time_ms !== undefined
                          ? `${sub.execution_time_ms} ms`
                          : '—'}
                      </td>
                      <td style={{ fontSize: '0.8rem', color: '#64748b' }}>{formatDate(sub.created_at)}</td>
                      <td style={{ fontSize: '0.8rem', color: '#38bdf8' }}>
                        {isExpanded ? 'Hide ▲' : 'Inspect ▼'}
                      </td>
                    </tr>

                    {/* Expanded details row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} style={{ backgroundColor: '#090d16', padding: '1rem 1.5rem', borderBottom: '1px solid #1e293b' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                              <span>Full ID: <code style={{ color: '#38bdf8' }}>{sub.id}</code></span>
                              <span>Completed: {sub.completed_at ? formatDate(sub.completed_at) : 'N/A'}</span>
                            </div>

                            {sub.error_message && (
                              <div className="error-box" style={{ fontSize: '0.8rem' }}>
                                {sub.error_message}
                              </div>
                            )}

                            {sub.testcase_results && sub.testcase_results.length > 0 ? (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.25rem' }}>
                                {sub.testcase_results.map((tc) => (
                                  <div
                                    key={tc.testcase_index}
                                    style={{
                                      border: '1px solid #1e293b',
                                      borderRadius: '6px',
                                      padding: '0.35rem 0.65rem',
                                      backgroundColor: '#111827',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '0.5rem',
                                      fontSize: '0.75rem',
                                    }}
                                  >
                                    <span style={{ color: '#94a3b8' }}>TC #{tc.testcase_index + 1}:</span>
                                    <StatusBadge status={tc.status} />
                                    <span style={{ color: '#64748b', fontFamily: 'monospace' }}>{tc.duration_ms}ms</span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>No testcase breakdown details.</div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>

          {/* Pagination Controls */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.85rem 1.25rem', borderTop: '1px solid #1e293b', fontSize: '0.85rem', color: '#94a3b8' }}>
            <span>
              Showing {submissions.length > 0 ? offset + 1 : 0}–{Math.min(offset + limit, total)} of {total} submissions
            </span>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                className="btn-secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                ◀ Previous
              </button>
              <span>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn-secondary"
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
              >
                Next ▶
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
