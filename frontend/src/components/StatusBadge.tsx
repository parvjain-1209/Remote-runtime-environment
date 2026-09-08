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

  const formatBadgeInfo = (st: string) => {
    switch (st.toUpperCase()) {
      case 'ACCEPTED':
        return { label: 'Accepted', icon: '✓' };
      case 'WRONG_ANSWER':
        return { label: 'Wrong Answer', icon: '✗' };
      case 'TIME_LIMIT_EXCEEDED':
        return { label: 'Time Limit Exceeded', icon: '⏱' };
      case 'MEMORY_LIMIT_EXCEEDED':
        return { label: 'Memory Limit Exceeded', icon: '💾' };
      case 'OUTPUT_LIMIT_EXCEEDED':
        return { label: 'Output Limit Exceeded', icon: '📄' };
      case 'COMPILATION_ERROR':
        return { label: 'Compilation Error', icon: '⚠' };
      case 'RUNTIME_ERROR':
        return { label: 'Runtime Error', icon: '⚡' };
      case 'SYSTEM_ERROR':
        return { label: 'System Error', icon: '⚙' };
      case 'QUEUED':
        return { label: 'Queued', icon: null };
      case 'COMPILING':
        return { label: 'Compiling...', icon: null };
      case 'RUNNING':
        return { label: 'Evaluating...', icon: null };
      default:
        return { label: st, icon: null };
    }
  };

  const { label, icon } = formatBadgeInfo(status);

  return (
    <span className={`status-badge ${normalized} ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}>
      {isPending ? (
        <span className="pulse-spinner" style={{ width: '11px', height: '11px' }}></span>
      ) : icon ? (
        <span style={{ fontSize: '0.85em', lineHeight: 1 }}>{icon}</span>
      ) : null}
      <span>{label}</span>
    </span>
  );
};
