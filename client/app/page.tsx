'use client';

import SchemaSplitEditor from '@/components/editor/SchemaSplitEditor';
import ComparisonResults from '@/components/results/ComparisonResults';
import MetricsDashboard from '@/components/results/MetricsDashboard';
import AppNavigation from '@/components/layout/AppNavigation';
import HeroSection from '@/components/layout/HeroSection';
import AppFooter from '@/components/layout/AppFooter';
import { useCompare } from '@/hooks/useCompare';

export default function Home() {
  const { result, loading, error, parseErrors, executeCompare, resetCompare } = useCompare();

  return (
    <main className="min-h-screen bg-black text-zinc-50 flex flex-col" role="main">
      <AppNavigation />

      <section className="flex-1 max-w-7xl w-full mx-auto px-4 py-12 flex flex-col gap-8" aria-label="Schema comparison tool">
        <HeroSection />

        {result && (
          <div className="w-full" aria-label="Comparison metrics">
            <MetricsDashboard />
          </div>
        )}

        <div
          className="w-full bg-zinc-900/50 border border-zinc-800/60 rounded-2xl p-6 shadow-2xl shadow-black/40 hover:border-zinc-700 hover:bg-zinc-900 transition-all duration-300"
          aria-label="SQL schema editor"
        >
          <SchemaSplitEditor
            onCompare={executeCompare}
            onReset={resetCompare}
            isLoading={loading}
            parseErrors={parseErrors}
          />
        </div>

        {result && (
          <div className="w-full border-t border-zinc-800/60 pt-8" aria-label="Comparison results">
            <ComparisonResults result={result} />
          </div>
        )}
      </section>

      <AppFooter />
    </main>
  );
}