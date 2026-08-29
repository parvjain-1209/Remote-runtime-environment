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
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('All');

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

  const filteredProblems = problems.filter((p) => {
    const matchesSearch =
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.tags && p.tags.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesDifficulty =
      selectedDifficulty === 'All' ||
      p.difficulty.toLowerCase() === selectedDifficulty.toLowerCase();

    return matchesSearch && matchesDifficulty;
  });

  const getDifficultyBadge = (difficulty: string) => {
    const diff = difficulty.toLowerCase();
    let bg = 'rgba(16, 185, 129, 0.12)';
    let color = '#34d399';
    let border = 'rgba(16, 185, 129, 0.3)';

    if (diff === 'medium') {
      bg = 'rgba(245, 158, 11, 0.12)';
      color = '#fbbf24';
      border = 'rgba(245, 158, 11, 0.3)';
    } else if (diff === 'hard') {
      bg = 'rgba(239, 68, 68, 0.12)';
      color = '#f87171';
      border = 'rgba(239, 68, 68, 0.3)';
    }

    return (
      <span
        style={{
          backgroundColor: bg,
          color: color,
          border: `1px solid ${border}`,
          padding: '0.15rem 0.6rem',
          borderRadius: '9999px',
          fontSize: '0.75rem',
          fontWeight: 600,
        }}
      >
        {difficulty}
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc' }}>Problem Catalog</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Select a problem to write, submit, and judge your C++ code in a secure container sandbox.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Difficulty Filter Tabs */}
          <div style={{ display: 'flex', backgroundColor: '#0b0f19', border: '1px solid #1e293b', borderRadius: '8px', padding: '0.2rem' }}>
            {['All', 'Easy', 'Medium', 'Hard'].map((diff) => (
              <button
                key={diff}
                onClick={() => setSelectedDifficulty(diff)}
                style={{
                  background: selectedDifficulty === diff ? '#1e293b' : 'transparent',
                  color: selectedDifficulty === diff ? '#38bdf8' : '#94a3b8',
                  border: 'none',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {diff}
              </button>
            ))}
          </div>

          <input
            type="text"
            placeholder="Search title, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              backgroundColor: '#0b0f19',
              border: '1px solid #1e293b',
              color: '#f8fafc',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              fontSize: '0.9rem',
              minWidth: '220px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {loading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
          <div className="pulse-spinner" style={{ width: '24px', height: '24px', margin: '0 auto 1rem auto' }}></div>
          Fetching problem catalog from backend API...
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
          No problems found matching criteria.
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', flex: 1 }}>
                  #{prob.id}. {prob.title}
                </h3>
                {getDifficultyBadge(prob.difficulty)}
              </div>

              {/* Tags */}
              {prob.tags && (
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                  {prob.tags.split(',').map((tag, idx) => (
                    <span
                      key={idx}
                      style={{
                        backgroundColor: '#1e293b',
                        color: '#94a3b8',
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.45rem',
                        borderRadius: '4px',
                        fontWeight: 500,
                      }}
                    >
                      {tag.trim()}
                    </span>
                  ))}
                </div>
              )}

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
