import React, { useMemo } from 'react';

interface CodeEditorProps {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  onResetTemplate?: () => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  disabled = false,
  onResetTemplate,
}) => {
  const lineCount = useMemo(() => {
    return Math.max(1, value.split('\n').length);
  }, [value]);

  const lineNumbers = useMemo(() => {
    return Array.from({ length: lineCount }, (_, i) => i + 1).join('\n');
  }, [lineCount]);

  return (
    <div className="editor-container">
      <div className="editor-header">
        <div className="flex items-center gap-2" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38bdf8' }}>Language:</span>
          <span style={{ fontSize: '0.8rem', backgroundColor: '#1e293b', padding: '0.15rem 0.5rem', borderRadius: '4px', color: '#f8fafc', fontWeight: 500 }}>
            C++17 (g++)
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
          placeholder="// Type your C++ solution here..."
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
        />
      </div>
    </div>
  );
};
