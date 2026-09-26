import React from 'react';
import { ShieldCheck, AlertTriangle, ShieldAlert } from 'lucide-react';

interface ConfidenceMeterProps {
  score: number; // 0 to 100
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  score,
  showLabel = true,
  size = 'md'
}) => {
  const rounded = Math.round(score);

  // Color tiering
  let colorClass = 'text-emerald-700 bg-emerald-50 border-emerald-300';
  let barClass = 'bg-emerald-600';
  let icon = <ShieldCheck className="w-4 h-4 text-emerald-600" />;
  let tierLabel = 'No rule mismatch detected';

  if (score < 60) {
    colorClass = 'text-rose-700 bg-rose-50 border-rose-300';
    barClass = 'bg-rose-600';
    icon = <ShieldAlert className="w-4 h-4 text-rose-600" />;
    tierLabel = 'Rule issues flagged';
  } else if (score < 85) {
    colorClass = 'text-amber-700 bg-amber-50 border-amber-300';
    barClass = 'bg-amber-500';
    icon = <AlertTriangle className="w-4 h-4 text-amber-600" />;
    tierLabel = 'Officer review recommended';
  }

  if (size === 'sm') {
    return (
      <div className="flex items-center gap-1.5">
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-semibold ${colorClass}`}>
          {icon}
          <span title="Heuristic scheme-rule indicator; not OCR confidence or a probability">{rounded}%</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          {icon}
          <span className="text-xs font-medium text-slate-700">{tierLabel}</span>
        </div>
        <span className="text-xs font-bold text-slate-900" title="Heuristic scheme-rule indicator; not OCR confidence or a probability">{score.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barClass}`}
          style={{ width: `${Math.max(5, Math.min(100, score))}%` }}
        />
      </div>
    </div>
  );
};
