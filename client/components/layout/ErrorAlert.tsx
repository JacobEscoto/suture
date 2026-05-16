'use client';

import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { ParseError } from '@/types/api';

interface ErrorItemProps {
  error: ParseError;
}

const ErrorItem = React.memo(({ error }: ErrorItemProps) => {
  return (
    <div className="bg-zinc-900/50 rounded-lg p-3 border border-rose-500/10">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">
          {error.editor === 'v1' ? 'Base Schema' : 'Destination Schema'}
          {error.line_number && ` (Line ${error.line_number})`}
        </span>
        <span className="text-[10px] font-mono bg-rose-500/10 px-2 py-0.5 rounded text-rose-400 uppercase">
          {error.error_type}
        </span>
      </div>

      <p className="text-sm text-rose-300/90 mb-2">{error.message}</p>

      {error.statement && (
        <div className="bg-zinc-950 border border-zinc-800 rounded p-2 mb-2">
          <code className="text-xs text-zinc-400 font-mono">{error.statement}</code>
        </div>
      )}

      {error.suggestion && (
        <div className="flex items-start gap-2 text-xs text-amber-400 mt-2 bg-amber-500/10 p-2 rounded">
          <span className="font-bold">Suggestion:</span>
          <span>{error.suggestion}</span>
        </div>
      )}
    </div>
  );
});

ErrorItem.displayName = 'ErrorItem';

interface ErrorAlertProps {
  message?: string;
  errors?: ParseError[];
  onDismiss?: () => void;
}

const ErrorAlert = React.memo(({ message, errors, onDismiss }: ErrorAlertProps) => {
  if (!message && !errors?.length) return null;

  return (
    <div className="w-full bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-bold text-rose-400 mb-2">Error Parsing Schemas</h3>

          {message && (
            <p className="text-sm text-rose-300/80 mb-3">{message}</p>
          )}

          {errors && errors.length > 0 && (
            <div className="space-y-3">
              {errors.map((error) => {
                const stableKey = `${error.editor}-${error.line_number || 0}-${error.error_type}-${error.message.substring(0, 10)}`;
                return <ErrorItem key={stableKey} error={error} />;
              })}
            </div>
          )}
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-rose-400 hover:text-rose-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
});

ErrorAlert.displayName = 'ErrorAlert';
export default ErrorAlert;