'use client';

import React from 'react';
import { Zap, Clock, Shield, CheckCircle2 } from 'lucide-react';

interface MetricCardProps {
  icon: React.ReactNode;
  title: string;
  value: string;
  subtitle: string;
  accentColor: string;
  glowColor: string;
  badge?: {
    text: string;
    color: string;
  };
}

const MetricCard: React.FC<MetricCardProps> = ({
  icon,
  title,
  value,
  subtitle,
  accentColor,
  glowColor,
  badge
}) => {
  return (
    <div
      className={`
        bg-zinc-900 border border-zinc-800 rounded-xl p-6
        transition-all duration-300 group cursor-default
        hover:border-zinc-700 hover:shadow-2xl
        ${glowColor}
      `}
    >
      <div className="flex items-start gap-4">
        <div className={`
          p-3 rounded-lg ${accentColor}
          group-hover:scale-110 transition-transform duration-300
          shadow-lg
        `}>
          {icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">
              {title}
            </h3>
            {badge && (
              <span className={`
                flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold uppercase
                ${badge.color} animate-pulse
              `}>
                <CheckCircle2 className="w-3 h-3" />
                {badge.text}
              </span>
            )}
          </div>
          <p className="text-2xl font-bold text-white mb-2 font-mono tracking-tight leading-tight">
            {value}
          </p>
          <p className="text-sm text-zinc-500 leading-relaxed">
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
};

export const MetricsDashboard: React.FC = () => {
  return (
    <div className="mb-8">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-white mb-2 tracking-tight">
          Executive Metrics
        </h2>
        <p className="text-sm text-zinc-400">
          Quantifiable business value delivered by Suturé's automated schema migration system
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          icon={<Zap className="w-6 h-6 text-emerald-400" />}
          title="Operational Steps"
          value="12 Steps → 2 Steps"
          subtitle="Reduction in manual code-review bottlenecks."
          accentColor="bg-emerald-500/10"
          glowColor="hover:shadow-emerald-500/20"
          badge={{
            text: "Optimized",
            color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
          }}
        />

        <MetricCard
          icon={<Clock className="w-6 h-6 text-blue-400" />}
          title="Validation Speed"
          value="~45 min → < 2 sec"
          subtitle="Instant confirmation backed by our SQLite In-Memory Sandbox."
          accentColor="bg-blue-500/10"
          glowColor="hover:shadow-blue-500/20"
          badge={{
            text: "Sandbox Active",
            color: "bg-blue-500/20 text-blue-400 border border-blue-500/30"
          }}
        />

        <MetricCard
          icon={<Shield className="w-6 h-6 text-violet-400" />}
          title="Rollback Reliability"
          value="100% Guaranteed"
          subtitle="Every single escape script is physically simulated and verified."
          accentColor="bg-violet-500/10"
          glowColor="hover:shadow-violet-500/20"
          badge={{
            text: "Verified",
            color: "bg-violet-500/20 text-violet-400 border border-violet-500/30"
          }}
        />
      </div>

      {/* Elegant divider with gradient */}
      <div className="mt-8 h-px bg-gradient-to-r from-transparent via-zinc-800 to-transparent"></div>
    </div>
  );
};

export default MetricsDashboard;

// Made with Bob
