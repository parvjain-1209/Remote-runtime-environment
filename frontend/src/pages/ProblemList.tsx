import React, { useEffect, useState } from 'react';
import { fetchProblems } from '../services/api';
import { ProblemListItem } from '../types';

interface ProblemListProps {
  onSelectProblem: (id: number) => void;
}

export const ProblemList: React.FC<ProblemListProps> = ({ onSelectProblem }) => {
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProblems();
      setProblems(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load problem list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredProblems = problems.filter((p) =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }}>Problems</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Select a problem to write, submit, and judge your C++ code in a secure container sandbox.
          </p>
        </div>

        <input
          type="text"
          placeholder="Search problems..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            backgroundColor: '#0b0f19',
            border: '1px solid #1e293b',
            color: '#f8fafc',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            fontSize: '0.9rem',
            minWidth: '260px',
            outline: 'none',
          }}
        />
      </div>

      {loading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
          <div className="pulse-spinner" style={{ width: '24px', height: '24px', margin: '0 auto 1rem auto' }}></div>
          Fetching problems from backend API...
        </div>
      )}

      {error && (
        <div className="error-box" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button className="btn-secondary" onClick={loadData}>Retry</button>
        </div>
      )}

      {!loading && !error && filteredProblems.length === 0 && (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b', backgroundColor: '#111827', borderRadius: '12px', border: '1px solid #1e293b' }}>
          No problems found.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1.25rem' }}>
        {filteredProblems.map((prob) => (
          <div
            key={prob.id}
            className="card"
            style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
            onClick={() => onSelectProblem(prob.id)}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#38bdf8' }}>
                  #{prob.id}. {prob.title}
                </h3>
                <span style={{ fontSize: '0.75rem', backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '0.15rem 0.5rem', borderRadius: '4px' }}>
                  C++ Only
                </span>
              </div>

              <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1.25rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {prob.description}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.85rem', borderTop: '1px solid #1e293b', fontSize: '0.8rem', color: '#64748b' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <span>⏱️ {prob.time_limit_ms} ms</span>
                <span>💾 {prob.memory_limit_mb} MB</span>
              </div>
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>Solve →</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
