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
