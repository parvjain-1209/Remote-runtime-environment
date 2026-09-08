import React, { useMemo } from 'react';

interface CodeEditorProps {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  onResetTemplate?: () => void;
  language?: string;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  disabled = false,
  onResetTemplate,
  language = 'cpp',
}) => {
  const lineCount = useMemo(() => {
    return Math.max(1, value.split('\n').length);
  }, [value]);

  const lineNumbers = useMemo(() => {
    return Array.from({ length: lineCount }, (_, i) => i + 1).join('\n');
  }, [lineCount]);

  const languageLabel = useMemo(() => {
    switch (language?.toLowerCase()) {
      case 'python':
        return 'Python (3.11)';
      case 'java':
        return 'Java (OpenJDK 21)';
      case 'cpp':
      default:
        return 'C++17 (g++)';
    }
  }, [language]);

  const placeholder = useMemo(() => {
    switch (language?.toLowerCase()) {
      case 'python':
        return '# Type your Python solution here...';
      case 'java':
        return '// Type your Java solution here (class Main)...';
      case 'cpp':
      default:
        return '// Type your C++ solution here...';
    }
  }, [language]);

  return (
    <div className="editor-container">
      <div className="editor-header">
        <div className="flex items-center gap-2" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8' }}>Language:</span>
          <span style={{ fontSize: '0.8rem', backgroundColor: '#1e293b', padding: '0.15rem 0.5rem', borderRadius: '4px', color: '#f8fafc', fontWeight: 500 }}>
            {languageLabel}
          </span>
        </div>
        {onResetTemplate && (
          <button
            type="button"
            className="btn-secondary"
            onClick={onResetTemplate}
            disabled={disabled}
            style={{ fontSize: '0.75rem', padding: '0.2rem 0.55rem' }}
          >
            Reset Starter Template
          </button>
        )}
      </div>

      <div className="editor-body">
        <pre className="line-numbers">{lineNumbers}</pre>
        <textarea
          className="code-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
        />
      </div>
    </div>
  );
};
