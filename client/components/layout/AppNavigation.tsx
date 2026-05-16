'use client';

import React from 'react';

interface AppNavigationProps {
  version?: string;
}

const AppNavigation = React.memo(({ version = 'v1.0.0-beta' }: AppNavigationProps) => {
  return (
    <nav className="border-b border-zinc-900 px-6 py-4 flex items-center justify-between bg-zinc-950/50 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-2xl tracking-tight">
          Sutur<span className="text-[rgb(78,56,245)]">é</span>
        </span>
      </div>
      <div className="text-xs text-zinc-500 bg-zinc-900 px-2.5 py-1 rounded-full font-mono">
        {version}
      </div>
    </nav>
  );
});

AppNavigation.displayName = 'AppNavigation';

export default AppNavigation;

// Made with Bob
