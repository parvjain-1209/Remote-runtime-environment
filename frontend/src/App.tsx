import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { ProblemList } from './pages/ProblemList';
import { ProblemWorkspace } from './pages/ProblemWorkspace';
import { SubmissionHistory } from './pages/SubmissionHistory';

type ViewMode = 'problems' | 'workspace' | 'history';

export const App: React.FC = () => {
  const [view, setView] = useState<ViewMode>('problems');
  const [selectedProblemId, setSelectedProblemId] = useState<number | null>(null);

  const handleSelectProblem = (id: number) => {
    setSelectedProblemId(id);
    setView('workspace');
  };

  const handleNavigate = (targetView: 'problems' | 'history') => {
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
      </main>
    </div>
  );
};

export default App;
