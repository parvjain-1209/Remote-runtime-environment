import React from 'react';
import { SubmissionStatus } from '../types';

interface StatusBadgeProps {
  status: SubmissionStatus;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const normalized = (status || 'QUEUED').toLowerCase();

  const isPending =
    normalized === 'queued' || normalized === 'compiling' || normalized === 'running';

  const formatLabel = (st: string) => {
    switch (st.toUpperCase()) {
      case 'ACCEPTED':
        return 'Accepted';
      case 'WRONG_ANSWER':
        return 'Wrong Answer';
      case 'TIME_LIMIT_EXCEEDED':
        return 'Time Limit Exceeded';
      case 'MEMORY_LIMIT_EXCEEDED':
        return 'Memory Limit Exceeded';
      case 'OUTPUT_LIMIT_EXCEEDED':
        return 'Output Limit Exceeded';
      case 'COMPILATION_ERROR':
        return 'Compilation Error';
      case 'RUNTIME_ERROR':
        return 'Runtime Error';
      case 'SYSTEM_ERROR':
        return 'System Error';
      case 'QUEUED':
        return 'Queued';
      case 'COMPILING':
        return 'Compiling...';
      case 'RUNNING':
        return 'Running...';
      default:
        return st;
    }
  };

  return (
    <span className={`status-badge ${normalized} ${className}`}>
      {isPending && <span className="pulse-spinner"></span>}
      {formatLabel(status)}
    </span>
  );
};
