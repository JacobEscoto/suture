'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { History, Home } from 'lucide-react';

interface AppNavigationProps {
  version?: string;
}

const AppNavigation = React.memo(({ version = 'v1.0.0-beta' }: AppNavigationProps) => {
  const pathname = usePathname();

  return (
    <nav className="border-b border-zinc-900 px-6 py-4 flex items-center justify-between bg-zinc-950/50 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-6">
        <Link href="/" className="font-semibold text-2xl tracking-tight hover:opacity-80 transition-opacity">
          Sutur<span className="text-[rgb(78,56,245)]">é</span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="/"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              pathname === '/'
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
          >
            <Home className="w-4 h-4" />
            Editor
          </Link>
          <Link
            href="/history"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              pathname === '/history'
                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
            }`}
          >
            <History className="w-4 h-4" />
            History
          </Link>
        </div>
      </div>

      <div className="text-xs text-zinc-500 bg-zinc-900 px-2.5 py-1 rounded-full font-mono">
        {version}
      </div>
    </nav>
  );
});

AppNavigation.displayName = 'AppNavigation';

export default AppNavigation;
