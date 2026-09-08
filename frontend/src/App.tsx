import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { AuthProvider } from './context/AuthContext';
import { Dashboard } from './pages/Dashboard';
import { ProblemList } from './pages/ProblemList';
import { ProblemWorkspace } from './pages/ProblemWorkspace';
import { SubmissionHistory } from './pages/SubmissionHistory';

type ViewMode = 'problems' | 'workspace' | 'history' | 'dashboard';

const MainApp: React.FC = () => {
  const [view, setView] = useState<ViewMode>('problems');
  const [selectedProblemId, setSelectedProblemId] = useState<number | null>(null);

  const handleSelectProblem = (id: number) => {
    setSelectedProblemId(id);
    setView('workspace');
  };

  const handleNavigate = (targetView: 'problems' | 'history' | 'dashboard') => {
    setView(targetView);
  };

  return (
    <div className="app-container">
      <Navbar currentView={view} onNavigate={handleNavigate} />

      <main className="main-content">
        {view === 'problems' && (
          <ProblemList onSelectProblem={handleSelectProblem} />
        )}

        {view === 'workspace' && selectedProblemId !== null && (
          <ProblemWorkspace
            problemId={selectedProblemId}
            onBack={() => setView('problems')}
          />
        )}

        {view === 'history' && (
          <SubmissionHistory onSelectProblem={handleSelectProblem} />
        )}

        {view === 'dashboard' && (
          <Dashboard onSelectProblem={handleSelectProblem} />
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-inner">
          <div className="footer-left">
            <span className="footer-brand-title">Remote Runtime Environment</span>
            <span className="footer-separator">•</span>
            <span className="footer-subtitle">Distributed Multi-Language Online Judge & Code Execution Platform</span>
          </div>
          <div className="footer-right">
            <span className="footer-badge">C++17</span>
            <span className="footer-badge">Python 3.11</span>
            <span className="footer-badge">Java 21</span>
            <span className="footer-badge">Docker Sandboxing</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
};

export default App;
