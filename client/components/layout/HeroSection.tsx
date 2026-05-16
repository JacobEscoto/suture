'use client';

import React from 'react';

const HeroSection = React.memo(() => {
  return (
    <div className="flex flex-col gap-3 max-w-2xl">
      <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-zinc-50 via-zinc-200 to-zinc-500 bg-clip-text text-transparent antialiased">
        Enterprise SQL Migration Generator
      </h1>
      <p className="text-sm md:text-base text-zinc-400 leading-relaxed">
        Paste your old and new schematics. Suturé takes care of calculating the structural differences and writing your production-ready scripts with 100% sandbox verification.
      </p>
    </div>
  );
});

HeroSection.displayName = 'HeroSection';

export default HeroSection;

// Made with Bob
