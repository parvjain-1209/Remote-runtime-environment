import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const { login, register } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (tab === 'login') {
        await login({ username, password });
      } else {
        await register({ username, email, password });
      }
      onClose();
      // Reset form
      setUsername('');
      setEmail('');
      setPassword('');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '420px',
          backgroundColor: '#111827',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '1.75rem',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
            {tab === 'login' ? 'Welcome Back' : 'Create Account'}
          </h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.25rem', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', backgroundColor: '#0b0f19', border: '1px solid #1e293b', borderRadius: '8px', padding: '0.2rem', marginBottom: '1.25rem' }}>
          <button
            style={{
              flex: 1,
              background: tab === 'login' ? '#1e293b' : 'transparent',
              color: tab === 'login' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              padding: '0.45rem',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
            onClick={() => { setTab('login'); setError(null); }}
          >
            Log In
          </button>
          <button
            style={{
              flex: 1,
              background: tab === 'register' ? '#1e293b' : 'transparent',
              color: tab === 'register' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              padding: '0.45rem',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
            onClick={() => { setTab('register'); setError(null); }}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="error-box" style={{ marginBottom: '1rem', padding: '0.65rem 0.85rem', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '0.35rem' }}>
              Username
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. coder123"
              style={{
                width: '100%',
                backgroundColor: '#0b0f19',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                padding: '0.6rem 0.85rem',
                color: '#f8fafc',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {tab === 'register' && (
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '0.35rem' }}>
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="coder@example.com"
                style={{
                  width: '100%',
                  backgroundColor: '#0b0f19',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '0.6rem 0.85rem',
                  color: '#f8fafc',
                  fontSize: '0.9rem',
                  outline: 'none',
                }}
              />
            </div>
          )}

          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '0.35rem' }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%',
                backgroundColor: '#0b0f19',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                padding: '0.6rem 0.85rem',
                color: '#f8fafc',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={submitting}
            style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem', padding: '0.65rem' }}
          >
            {submitting ? (
              <span className="pulse-spinner"></span>
            ) : tab === 'login' ? (
              'Log In'
            ) : (
              'Create Account'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
