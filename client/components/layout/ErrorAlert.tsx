'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorAlertProps {
  message: string;
}

const ErrorAlert = React.memo(({ message }: ErrorAlertProps) => {
  return (
    <div className="w-full bg-rose-500/10 border border-rose-500/20 text-rose-400 p-4 rounded-xl text-sm font-mono whitespace-pre-wrap flex items-start gap-3">
      <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
      <div>
        <span className="font-bold">Server Error:</span> {message}
      </div>
    </div>
  );
});

ErrorAlert.displayName = 'ErrorAlert';

export default ErrorAlert;

// Made with Bob
