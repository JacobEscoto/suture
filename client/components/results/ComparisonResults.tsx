'use client';

import React, { useState, useCallback } from 'react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

import {
  CheckSquare,
  AlertCircle,
  Trash2,
  Layers,
  Copy,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Plus,
  Minus,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck
} from 'lucide-react';
import { AnalysisResult, TableChange, ColumnChange } from '@/types/api';

interface ComparisonResultsProps {
  result: AnalysisResult;
}

const BADGE_STYLES = {
  added: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  deleted: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  modified: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

const TableChangeCard = React.memo(function TableChangeCard({ table }: { table: TableChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const badgeColors = BADGE_STYLES[table.change_type] || BADGE_STYLES.modified;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden transition-all">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-zinc-800/50 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 text-xs font-mono font-medium rounded border ${badgeColors}`}>
            {table.change_type.toUpperCase()}
          </span>
          <span className="text-sm font-semibold text-zinc-200 font-mono">{table.name}</span>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
      </button>

      {isOpen && (
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/40 flex flex-col gap-4 animate-fade-in">
          {table.columns && table.columns.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Columns</h4>
              <div className="grid grid-cols-1 gap-2">
                {table.columns.map((col) => (
                  <div key={col.name} className="flex items-center justify-between bg-zinc-900/60 border border-zinc-800/80 p-3 rounded-lg font-mono text-xs">
                    <div className="flex items-center gap-2">
                      {col.change_type === 'added' && <Plus className="w-3.5 h-3.5 text-emerald-500" />}
                      {col.change_type === 'deleted' && <Minus className="w-3.5 h-3.5 text-rose-500" />}
                      {col.change_type === 'modified' && <RefreshCw className="w-3.5 h-3.5 text-amber-500" />}
                      <span className="text-zinc-200 font-semibold">{col.name}</span>
                    </div>
                    <div className="text-zinc-400 flex items-center gap-2">
                      {col.change_type === 'modified' && col.old_data_type ? (
                        <>
                          <span className="line-through text-zinc-600">{col.old_data_type.toLowerCase()}</span>
                          <span className="text-zinc-500">→</span>
                          <span className="text-amber-400">{col.data_type?.toLowerCase()}</span>
                        </>
                      ) : (
                        <span className={col.change_type === 'added' ? 'text-emerald-400' : 'text-rose-400'}>
                          {col.data_type?.toLowerCase()}
                        </span>
                      )}
                      {col.nullable === false && <span className="text-rose-400/80 text-[10px] bg-rose-500/5 px-1.5 py-0.5 rounded border border-rose-500/10">NN</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {table.constraints && table.constraints.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Constraints</h4>
              <div className="flex flex-wrap gap-2">
                {table.constraints.map((c) => (
                  <span key={c.name || c.definition} className="px-2 py-1 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono">
                    {c.change_type === 'added' ? '+ ' : '- '} {c.name || c.constraint_type} ({c.columns.join(', ')})
                  </span>
                ))}
              </div>
            </div>
          )}

          {table.indexes && table.indexes.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Indexes</h4>
              <div className="flex flex-wrap gap-2">
                {table.indexes.map((idx) => (
                  <span key={idx.name} className="px-2 py-1 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-xs font-mono">
                    {idx.change_type === 'added' ? '+ ' : '- '} {idx.name} [{idx.columns.join(', ')}]
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

const RiskMeter = React.memo(function RiskMeter({ blastRadius }: { blastRadius: AnalysisResult['blast_radius'] }) {
  const { risk_level, score, destructive_actions_count } = blastRadius;

  const riskConfig = {
    LOW: {
      color: 'emerald',
      icon: ShieldCheck,
      bgClass: 'bg-emerald-500/10',
      borderClass: 'border-emerald-500/20',
      textClass: 'text-emerald-400',
      progressClass: 'bg-emerald-500',
      message: 'Safe migration with minimal risk'
    },
    MEDIUM: {
      color: 'amber',
      icon: Shield,
      bgClass: 'bg-amber-500/10',
      borderClass: 'border-amber-500/20',
      textClass: 'text-amber-400',
      progressClass: 'bg-amber-500',
      message: 'Moderate risk - review breaking changes'
    },
    CRITICAL: {
      color: 'rose',
      icon: ShieldAlert,
      bgClass: 'bg-rose-500/10',
      borderClass: 'border-rose-500/20',
      textClass: 'text-rose-400',
      progressClass: 'bg-rose-500',
      message: 'High risk - data loss possible'
    }
  };

  const config = riskConfig[risk_level];
  const Icon = config.icon;

  return (
    <div className={`${config.bgClass} border ${config.borderClass} rounded-xl p-5 flex flex-col gap-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Icon className={`w-6 h-6 ${config.textClass}`} />
          <div className="flex flex-col">
            <span className={`text-sm font-bold ${config.textClass} uppercase tracking-wide`}>
              Risk Level: {risk_level}
            </span>
            <span className="text-xs text-zinc-400 font-medium">{config.message}</span>
          </div>
        </div>
        <div className="flex flex-col items-end">
          <span className={`text-2xl font-bold ${config.textClass}`}>{score}%</span>
          <span className="text-xs text-zinc-500 font-medium">Risk Score</span>
        </div>
      </div>

      <div className="w-full bg-zinc-900 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full ${config.progressClass} transition-all duration-500 ease-out`}
          style={{ width: `${score}%` }}
        />
      </div>

      {destructive_actions_count > 0 && (
        <div className="flex items-center gap-2 text-xs">
          <AlertTriangle className={`w-3.5 h-3.5 ${config.textClass}`} />
          <span className="text-zinc-400">
            <span className={`font-bold ${config.textClass}`}>{destructive_actions_count}</span> destructive operation{destructive_actions_count !== 1 ? 's' : ''} detected
          </span>
        </div>
      )}
    </div>
  );
});

const ComparisonResults = React.memo(function ComparisonResults({ result }: ComparisonResultsProps) {
  const { changes_detected, migration_sql, rollback_sql, blast_radius, warnings } = result;
  const [activeTab, setActiveTab] = useState<'migration' | 'rollback'>('migration');

  const handleCopyMigration = useCallback(() => {
    navigator.clipboard.writeText(migration_sql);
    alert('Migration SQL copied to clipboard');
  }, [migration_sql]);

  const handleCopyRollback = useCallback(() => {
    navigator.clipboard.writeText(rollback_sql);
    alert('Rollback SQL copied to clipboard');
  }, [rollback_sql]);

  return (
    <div className="w-full flex flex-col gap-8 mt-8 animate-fade-in">

      {/* Risk Meter */}
      <RiskMeter blastRadius={blast_radius} />

      {warnings && warnings.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Migration Performance & Destructive Warnings</span>
          </div>
          <ul className="space-y-1.5 pl-6 list-disc text-xs font-mono text-amber-300/80">
            {warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center flex flex-col items-center justify-center gap-1">
          <CheckSquare className="w-5 h-5 text-emerald-500" />
          <div className="text-2xl font-bold text-emerald-500 mt-1">{changes_detected.summary.tables_added || 0}</div>
          <div className="text-xs text-zinc-400 font-medium">Tables Created</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center flex flex-col items-center justify-center gap-1">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          <div className="text-2xl font-bold text-amber-500 mt-1">{changes_detected.summary.tables_modified || 0}</div>
          <div className="text-xs text-zinc-400 font-medium">Modified Tables</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center flex flex-col items-center justify-center gap-1">
          <Trash2 className="w-5 h-5 text-rose-500" />
          <div className="text-2xl font-bold text-rose-500 mt-1">{changes_detected.summary.tables_deleted || 0}</div>
          <div className="text-xs text-zinc-400 font-medium">Deleted Tables</div>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center flex flex-col items-center justify-center gap-1">
          <Layers className="w-5 h-5 text-indigo-500" />
          <div className="text-2xl font-bold text-indigo-500 mt-1">
            {(changes_detected.summary.indexes_added || 0) + (changes_detected.summary.indexes_deleted || 0)}
          </div>
          <div className="text-xs text-zinc-400 font-medium">Affected Indices</div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Detailed Structural Changes</h3>
        <div className="flex flex-col gap-3">
          {changes_detected.tables.map((table) => (
            <TableChangeCard key={table.name} table={table} />
          ))}
          {changes_detected.tables.length === 0 && (
            <div className="bg-zinc-900/40 border border-zinc-800/60 p-6 rounded-xl text-center text-sm text-zinc-500 font-medium">
              No structural changes were detected in the tables.
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('migration')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                activeTab === 'migration'
                  ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              Migration Script (Up)
            </button>
            <button
              onClick={() => setActiveTab('rollback')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                activeTab === 'rollback'
                  ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              Rollback Script (Down)
            </button>
          </div>
          <button
            onClick={activeTab === 'migration' ? handleCopyMigration : handleCopyRollback}
            className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5" />
            Copy SQL
          </button>
        </div>

        <div className="w-full max-h-[500px] p-2 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-300 font-mono text-sm overflow-y-auto">
          <Editor
            value={activeTab === 'migration' ? migration_sql : rollback_sql}
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