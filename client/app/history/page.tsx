'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  History,
  Trash2,
  ShieldCheck,
  Shield,
  ShieldAlert,
  ArrowLeft,
  Calendar,
  TrendingUp,
  Database,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import AppNavigation from '@/components/layout/AppNavigation';
import AppFooter from '@/components/layout/AppFooter';

interface HistoryEntry {
  id: string;
  timestamp: string;
  risk_level: 'LOW' | 'MEDIUM' | 'CRITICAL';
  score: number;
  tables_added: number;
  tables_modified: number;
  tables_deleted: number;
}

const HISTORY_STORAGE_KEY = 'suture_deployment_history';

const RiskBadge = ({ level }: { level: 'LOW' | 'MEDIUM' | 'CRITICAL' }) => {
  const config = {
    LOW: {
      icon: ShieldCheck,
      bgClass: 'bg-emerald-500/10',
      borderClass: 'border-emerald-500/20',
      textClass: 'text-emerald-400',
    },
    MEDIUM: {
      icon: Shield,
      bgClass: 'bg-amber-500/10',
      borderClass: 'border-amber-500/20',
      textClass: 'text-amber-400',
    },
    CRITICAL: {
      icon: ShieldAlert,
      bgClass: 'bg-rose-500/10',
      borderClass: 'border-rose-500/20',
      textClass: 'text-rose-400',
    },
  };

  const { icon: Icon, bgClass, borderClass, textClass } = config[level];

  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${bgClass} ${borderClass}`}>
      <Icon className={`w-3.5 h-3.5 ${textClass}`} />
      <span className={`text-xs font-bold uppercase tracking-wide ${textClass}`}>{level}</span>
    </div>
  );
};

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setHistory(parsed);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = () => {
    if (confirm('Are you sure you want to clear all deployment history? This action cannot be undone.')) {
      localStorage.removeItem(HISTORY_STORAGE_KEY);
      setHistory([]);
    }
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(timestamp);
  };

  const stats = {
    total: history.length,
    low: history.filter((h) => h.risk_level === 'LOW').length,
    medium: history.filter((h) => h.risk_level === 'MEDIUM').length,
    critical: history.filter((h) => h.risk_level === 'CRITICAL').length,
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 flex flex-col">
      <AppNavigation />

      <section className="flex-1 max-w-7xl w-full mx-auto px-4 py-12 flex flex-col gap-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/')}
              className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 transition-colors"
              title="Back to Editor"
            >
              <ArrowLeft className="w-5 h-5 text-zinc-400" />
            </button>
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">
                <History className="w-8 h-8 text-indigo-400" />
                Deployment History
              </h1>
              <p className="text-sm text-zinc-400 mt-1">
                Track all schema comparison and migration activities
              </p>
            </div>
          </div>

          {history.length > 0 && (
            <button
              onClick={clearHistory}
              className="px-4 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 font-medium transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Clear History
            </button>
          )}
        </div>

        {/* Stats Cards */}
        {history.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col items-center justify-center gap-2">
              <Database className="w-6 h-6 text-indigo-400" />
              <div className="text-2xl font-bold text-indigo-400">{stats.total}</div>
              <div className="text-xs text-zinc-400 font-medium">Total Deployments</div>
            </div>
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 flex flex-col items-center justify-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <div className="text-2xl font-bold text-emerald-400">{stats.low}</div>
              <div className="text-xs text-zinc-400 font-medium">Low Risk</div>
            </div>
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex flex-col items-center justify-center gap-2">
              <Shield className="w-6 h-6 text-amber-400" />
              <div className="text-2xl font-bold text-amber-400">{stats.medium}</div>
              <div className="text-xs text-zinc-400 font-medium">Medium Risk</div>
            </div>
            <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 flex flex-col items-center justify-center gap-2">
              <ShieldAlert className="w-6 h-6 text-rose-400" />
              <div className="text-2xl font-bold text-rose-400">{stats.critical}</div>
              <div className="text-xs text-zinc-400 font-medium">Critical Risk</div>
            </div>
          </div>
        )}

        {/* History Table */}
        <div className="bg-zinc-900/30 border border-zinc-900/80 rounded-2xl overflow-hidden">
          {loading ? (
            <div className="p-12 flex flex-col items-center justify-center gap-4">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-sm text-zinc-400">Loading history...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="p-12 flex flex-col items-center justify-center gap-4">
              <History className="w-16 h-16 text-zinc-700" />
              <div className="text-center">
                <h3 className="text-lg font-semibold text-zinc-300 mb-2">No Deployment History</h3>
                <p className="text-sm text-zinc-500 mb-4">
                  Start comparing schemas to build your deployment history
                </p>
                <button
                  onClick={() => router.push('/')}
                  className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
                >
                  Go to Editor
                </button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-zinc-900/50 border-b border-zinc-800">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Timestamp
                      </div>
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      Risk Level
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      <div className="flex items-center justify-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Score
                      </div>
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      Added
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      Modified
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                      Deleted
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  {history.map((entry) => (
                    <tr
                      key={entry.id}
                      className="hover:bg-zinc-900/40 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-zinc-200">
                            {formatDate(entry.timestamp)}
                          </span>
                          <span className="text-xs text-zinc-500">
                            {formatRelativeTime(entry.timestamp)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <RiskBadge level={entry.risk_level} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span
                          className={`text-lg font-bold ${
                            entry.risk_level === 'LOW'
                              ? 'text-emerald-400'
                              : entry.risk_level === 'MEDIUM'
                              ? 'text-amber-400'
                              : 'text-rose-400'
                          }`}
                        >
                          {entry.score}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="text-sm font-semibold text-emerald-400">
                          +{entry.tables_added}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="text-sm font-semibold text-amber-400">
                          ~{entry.tables_modified}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="text-sm font-semibold text-rose-400">
                          -{entry.tables_deleted}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Info Banner */}
        {history.length > 0 && (
          <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-indigo-400 mb-1">
                History Storage Information
              </h4>
              <p className="text-xs text-zinc-400">
                Deployment history is stored locally in your browser. The last 100 entries are kept.
                Clearing browser data will remove this history.
              </p>
            </div>
          </div>
        )}
      </section>

      <AppFooter />
    </main>
  );
}

// Made with Bob
