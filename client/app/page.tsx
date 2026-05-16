'use client';

import React from 'react';
import SchemaSplitEditor from '@/components/editor/SchemaSplitEditor';
import ComparisonResults from '@/components/results/ComparisonResults';
import AppNavigation from '@/components/layout/AppNavigation';
import HeroSection from '@/components/layout/HeroSection';
import ErrorAlert from '@/components/layout/ErrorAlert';
import AppFooter from '@/components/layout/AppFooter';
import { useCompare } from '@/hooks/useCompare';

export default function Home() {
  const { result, loading, error, executeCompare } = useCompare();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 flex flex-col">
      <AppNavigation />

      <section className="flex-1 max-w-7xl w-full mx-auto px-4 py-12 flex flex-col gap-8">
        <HeroSection />

        <div className="w-full bg-zinc-900/30 border border-zinc-900/80 rounded-2xl p-6 shadow-2xl backdrop-blur-sm">
          <SchemaSplitEditor onCompare={executeCompare} isLoading={loading} />
        </div>

        {error && <ErrorAlert message={error} />}

        {result && (
          <div className="w-full border-t border-zinc-900 pt-4">
            <ComparisonResults result={result} />
          </div>
        )}
      </section>

      <AppFooter />
    </main>
  );
}

// Made with Bob
