'use client';

import React from 'react';

const AppFooter = React.memo(() => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-zinc-900 py-6 text-center text-xs text-zinc-600 font-mono mt-12">
      Suturé DevTool © {currentYear} // All rights reserved.
    </footer>
  );
});

AppFooter.displayName = 'AppFooter';

export default AppFooter;

// Made with Bob
