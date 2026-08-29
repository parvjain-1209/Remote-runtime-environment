import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchHealth } from '../services/api';
import { HealthResponse } from '../types';
import { AuthModal } from './AuthModal';

interface NavbarProps {
  currentView: 'problems' | 'workspace' | 'history';
  onNavigate: (view: 'problems' | 'history') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<boolean>(false);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const data = await fetchHealth();
        if (isMounted) {
          setHealth(data);
          setHealthError(false);
        }
      } catch (err) {
        if (isMounted) {
          setHealthError(true);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      <header className="navbar">
        <div className="navbar-inner">
          <div className="brand" onClick={() => onNavigate('problems')}>
            <div className="brand-icon">OJ</div>
            <span>GDG Remote Judge</span>
          </div>

          <div className="nav-links">
            <button
              className={`nav-button ${currentView === 'problems' || currentView === 'workspace' ? 'active' : ''}`}
              onClick={() => onNavigate('problems')}
            >
              Problems
            </button>
            <button
              className={`nav-button ${currentView === 'history' ? 'active' : ''}`}
              onClick={() => onNavigate('history')}
            >
              Submission History
            </button>

            <div className="health-badge" title={healthError ? 'Backend API Unreachable' : `API Status: ${health?.status || 'checking'}, Redis Stream: ${health?.redis ? 'Connected' : 'Disconnected'}`}>
              <span className={`health-dot ${healthError || !health?.redis ? 'error' : 'ok'}`}></span>
              <span className="text-slate-400">
                {healthError ? 'API Down' : health?.redis ? 'System Online' : 'Redis Offline'}
              </span>
            </div>

            {/* Auth Section */}
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: '0.5rem' }}>
                <span
                  style={{
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.25)',
                    padding: '0.25rem 0.65rem',
                    borderRadius: '9999px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                  }}
                >
                  👤 {user.username}
                </span>
                <button
                  className="btn-secondary"
                  onClick={logout}
                  style={{ fontSize: '0.8rem', padding: '0.25rem 0.6rem' }}
                >
                  Log Out
                </button>
              </div>
            ) : (
              <button
                className="btn-primary"
                onClick={() => setAuthModalOpen(true)}
                style={{ fontSize: '0.85rem', padding: '0.35rem 0.85rem', marginLeft: '0.5rem' }}
              >
                Log In / Register
              </button>
            )}
          </div>
        </div>
      </header>

      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </>
  );
};
