import React, { useEffect, useState } from 'react';
import { fetchHealth } from '../services/api';
import { HealthResponse } from '../types';

interface NavbarProps {
  currentView: 'problems' | 'workspace' | 'history';
  onNavigate: (view: 'problems' | 'history') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<boolean>(false);

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
        </div>
      </div>
    </header>
  );
};
