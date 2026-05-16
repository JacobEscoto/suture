'use client';

import React from 'react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

import { Copy } from 'lucide-react';
import { AnalysisResult } from '@/types/api';

interface ComparisonResultsProps {
  result: AnalysisResult;
}

const ComparisonResults = React.memo(function ComparisonResults({ result }: ComparisonResultsProps) {
  const { changes_detected, migration_sql } = result;

  const handleCopy = () => {
    navigator.clipboard.writeText(migration_sql);
    alert('¡Código copiado al portapapeles!');
  };

  return (
    <div className="w-full flex flex-col gap-8 mt-8 animate-fade-in">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
          <div className="text-2xl font-bold text-emerald-500">{changes_detected.summary.tables_added || 0}</div>
          <div className="text-xs text-zinc-400 font-medium mt-1">Tables Created</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
          <div className="text-2xl font-bold text-amber-500">{changes_detected.summary.tables_modified || 0}</div>
          <div className="text-xs text-zinc-400 font-medium mt-1">Modified Tables</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
          <div className="text-2xl font-bold text-rose-500">{changes_detected.summary.tables_deleted || 0}</div>
          <div className="text-xs text-zinc-400 font-medium mt-1">Deleted Tables</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
          <div className="text-2xl font-bold text-indigo-500">
            {(changes_detected.summary.indexes_added || 0) + (changes_detected.summary.indexes_deleted || 0)}
          </div>
          <div className="text-xs text-zinc-400 font-medium mt-1">Affected Indices</div>
        </div>
      </div>

      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 flex flex-col gap-4">
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Changes Detected</h3>
        <div className="flex flex-wrap gap-3">
          {changes_detected.tables.map((table, idx) => {
            const badgeColors =
              table.change_type === 'added' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              table.change_type === 'deleted' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
              'bg-amber-500/10 text-amber-400 border-amber-500/20';

            return (
              <span key={idx} className={`px-3 py-1.5 text-xs font-mono font-medium rounded-lg border ${badgeColors}`}>
                {table.name} ({table.change_type})
              </span>
            );
          })}
          {changes_detected.tables.length === 0 && (
            <span className="text-sm text-zinc-500 font-medium">No structural changes were detected in the tables.</span>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-zinc-400">Standalone Migration Script</label>
          <button
            onClick={handleCopy}
            className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5"/>
            Copy SQL
          </button>
        </div>
        <div className="w-full max-h-[500px] p-2 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-300 font-mono text-sm overflow-y-auto">
          <Editor
            value={migration_sql}
            onValueChange={() => {}}
            highlight={(code) => highlight(code, languages.sql, "sql")}
            padding={16}
            style={{
              fontFamily: '"Fira code", "Fira Mono", monospace',
              fontSize: 14,
            }}
            textareaClassName="outline-none pointer-events-none"
            readOnly
          />
        </div>
      </div>
    </div>
  );
});

export default ComparisonResults;