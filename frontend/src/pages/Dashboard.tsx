import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchUserStats, fetchUserSubmissions } from '../services/api';
import { SubmissionResponse, UserStatsResponse } from '../types';

interface DashboardProps {
  onSelectProblem: (id: number) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectProblem }) => {
  const { user } = useAuth();
  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [submissions, setSubmissions] = useState<SubmissionResponse[]>([]);
  const [totalSubs, setTotalSubs] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    const loadDashboardData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [statsData, subsData] = await Promise.all([
          fetchUserStats(),
          fetchUserSubmissions(10, 0),
        ]);

        if (isMounted) {
          setStats(statsData);
          setSubmissions(subsData.submissions);
          setTotalSubs(subsData.total);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load user statistics.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, [user]);

  if (!user) {
    return (
      <div style={{ maxWidth: '600px', margin: '4rem auto', textAlign: 'center' }}>
        <div className="card" style={{ padding: '3rem 2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔐</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.75rem', color: '#f8fafc' }}>
            Authentication Required
          </h2>
          <p style={{ color: '#94a3b8', marginBottom: '1.5rem', fontSize: '0.95rem' }}>
            Please log in or create an account to view your personal solver statistics, difficulty progress, and submission history.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px' }}>
        <div className="pulse-spinner" style={{ width: '36px', height: '36px' }}></div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="error-box" style={{ margin: '2rem 0' }}>
        {error || 'Unable to load dashboard metrics.'}
      </div>
    );
  }

  const getVerdictBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
        return <span className="status-badge status-accepted">ACCEPTED</span>;
      case 'WRONG_ANSWER':
        return <span className="status-badge status-wrong">WRONG ANSWER</span>;
      case 'TIME_LIMIT_EXCEEDED':
        return <span className="status-badge status-tle">TIME LIMIT EXCEEDED</span>;
      case 'COMPILATION_ERROR':
        return <span className="status-badge status-ce">COMPILATION ERROR</span>;
      default:
        return <span className="status-badge status-other">{status.replace('_', ' ')}</span>;
    }
  };

  const getDifficultyPercent = (level: string) => {
    const solved = stats.solved_by_difficulty[level] || 0;
    const total = stats.total_by_difficulty[level] || 0;
    if (total === 0) return 0;
    return Math.round((solved / total) * 100);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Profile Header Card */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.5rem',
          padding: '1.5rem 2rem',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          border: '1px solid #334155',
        }}
      >
        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            backgroundColor: '#38bdf8',
            color: '#0f172a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.75rem',
            fontWeight: 800,
            textTransform: 'uppercase',
            boxShadow: '0 4px 14px rgba(56, 189, 248, 0.35)',
          }}
        >
          {user.username.charAt(0)}
        </div>

        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
            {user.username}
          </h1>
          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.35rem', color: '#94a3b8', fontSize: '0.85rem' }}>
            <span>📧 {user.email}</span>
            <span>📅 Joined {new Date(user.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div
          style={{
            textAlign: 'right',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            padding: '0.75rem 1.25rem',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Acceptance Rate
          </span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#10b981', marginTop: '0.1rem' }}>
            {stats.acceptance_rate}%
          </div>
        </div>
      </div>

      {/* Key Metric Stat Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Solved Problems</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {stats.total_solved_problems}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Unique ACCEPTED problems
          </span>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #38bdf8' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Total Submissions</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {stats.total_submissions}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            All submission attempts
          </span>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #a855f7' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Attempted Problems</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {stats.total_attempted_problems}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Distinct problem attempts
          </span>
        </div>

        <div className="card" style={{ padding: '1.25rem', borderLeft: '4px solid #f59e0b' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Accepted Verdicts</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>
            {stats.verdict_counts['ACCEPTED'] || 0}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Passed all test cases
          </span>
        </div>
      </div>

      {/* Difficulty Breakdown & Verdict Summary Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {/* Difficulty Progress */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1.25rem' }}>
            Difficulty Breakdown
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Easy */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span className="badge badge-easy">Easy</span>
                <span style={{ color: '#94a3b8', fontWeight: 600 }}>
                  {stats.solved_by_difficulty['Easy'] || 0} / {stats.total_by_difficulty['Easy'] || 0} Solved
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: '#0b0f19', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${getDifficultyPercent('Easy')}%`,
                    backgroundColor: '#10b981',
                    borderRadius: '4px',
                    transition: 'width 0.4s ease',
                  }}
                ></div>
              </div>
            </div>

            {/* Medium */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span className="badge badge-medium">Medium</span>
                <span style={{ color: '#94a3b8', fontWeight: 600 }}>
                  {stats.solved_by_difficulty['Medium'] || 0} / {stats.total_by_difficulty['Medium'] || 0} Solved
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: '#0b0f19', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${getDifficultyPercent('Medium')}%`,
                    backgroundColor: '#f59e0b',
                    borderRadius: '4px',
                    transition: 'width 0.4s ease',
                  }}
                ></div>
              </div>
            </div>

            {/* Hard */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span className="badge badge-hard">Hard</span>
                <span style={{ color: '#94a3b8', fontWeight: 600 }}>
                  {stats.solved_by_difficulty['Hard'] || 0} / {stats.total_by_difficulty['Hard'] || 0} Solved
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: '#0b0f19', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${getDifficultyPercent('Hard')}%`,
                    backgroundColor: '#ef4444',
                    borderRadius: '4px',
                    transition: 'width 0.4s ease',
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Verdict Distribution Matrix */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '1.25rem' }}>
            Verdict Summary
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
            <div style={{ backgroundColor: '#0b0f19', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 700 }}>ACCEPTED</span>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                {stats.verdict_counts['ACCEPTED'] || 0}
              </div>
            </div>

            <div style={{ backgroundColor: '#0b0f19', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <span style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 700 }}>WRONG ANSWER</span>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                {stats.verdict_counts['WRONG_ANSWER'] || 0}
              </div>
            </div>

            <div style={{ backgroundColor: '#0b0f19', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <span style={{ fontSize: '0.75rem', color: '#f59e0b', fontWeight: 700 }}>TIME LIMIT EXCEEDED</span>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                {stats.verdict_counts['TIME_LIMIT_EXCEEDED'] || 0}
              </div>
            </div>

            <div style={{ backgroundColor: '#0b0f19', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b' }}>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>ERRORS / OTHER</span>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.2rem' }}>
                {(stats.verdict_counts['COMPILATION_ERROR'] || 0) +
                  (stats.verdict_counts['RUNTIME_ERROR'] || 0) +
                  (stats.verdict_counts['MEMORY_LIMIT_EXCEEDED'] || 0) +
                  (stats.verdict_counts['SYSTEM_ERROR'] || 0)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Personal Submissions */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Recent Personal Submissions ({totalSubs})
          </h3>
        </div>

        {submissions.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
            No submissions recorded yet for your account.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="problem-table">
              <thead>
                <tr>
                  <th>Submission ID</th>
                  <th>Problem ID</th>
                  <th>Language</th>
                  <th>Verdict</th>
                  <th>Exec Time</th>
                  <th>Memory</th>
                  <th>Submitted At</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub) => (
                  <tr key={sub.id}>
                    <td>
                      <code style={{ fontSize: '0.75rem', color: '#38bdf8' }}>
                        {sub.id.substring(0, 8)}...
                      </code>
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectProblem(sub.problem_id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#38bdf8',
                          fontWeight: 600,
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          padding: 0,
                        }}
                      >
                        Problem #{sub.problem_id}
                      </button>
                    </td>
                    <td>
                      <span className="badge" style={{ textTransform: 'uppercase', fontSize: '0.7rem' }}>
                        {sub.language}
                      </span>
                    </td>
                    <td>{getVerdictBadge(sub.status)}</td>
                    <td>{sub.execution_time_ms !== null && sub.execution_time_ms !== undefined ? `${sub.execution_time_ms} ms` : '—'}</td>
                    <td>{sub.memory_used_mb !== null && sub.memory_used_mb !== undefined ? `${sub.memory_used_mb} MB` : '—'}</td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {new Date(sub.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
