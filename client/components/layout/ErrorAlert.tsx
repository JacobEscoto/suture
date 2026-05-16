'use client';

import React from 'react';

interface ErrorAlertProps {
  message: string;
}

const ErrorAlert = React.memo(({ message }: ErrorAlertProps) => {
  return (
    <div className="w-full bg-rose-500/10 border border-rose-500/20 text-rose-400 p-4 rounded-xl text-sm font-mono whitespace-pre-wrap">
      <span className="font-bold">⚠️ Server Error:</span> {message}
    </div>
  );
});

ErrorAlert.displayName = 'ErrorAlert';

export default ErrorAlert;

// Made with Bob
