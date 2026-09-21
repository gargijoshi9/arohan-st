import React from 'react';
import { CheckCircle2, Clock, AlertCircle, XCircle, FileSearch } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '', size = 'md' }) => {
  const normalized = status.toUpperCase();

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs font-semibold px-2.5 py-1 gap-1.5',
    lg: 'text-sm font-semibold px-3 py-1.5 gap-2'
  }[size];

  switch (normalized) {
    case 'APPROVED':
      return (
        <span className={`inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 border border-emerald-300 ${sizeClasses} ${className}`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Approved</span>
        </span>
      );
    case 'SUBMITTED':
      return (
        <span className={`inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-200 ${sizeClasses} ${className}`}>
          <Clock className="w-3.5 h-3.5 text-blue-600" />
          <span>Submitted</span>
        </span>
      );
    case 'UNDER_REVIEW':
      return (
        <span className={`inline-flex items-center rounded-full bg-amber-50 text-amber-700 border border-amber-300 ${sizeClasses} ${className}`}>
          <FileSearch className="w-3.5 h-3.5 text-amber-600" />
          <span>Under Review</span>
        </span>
      );
    case 'DEFICIENT':
      return (
        <span className={`inline-flex items-center rounded-full bg-rose-50 text-rose-700 border border-rose-300 ${sizeClasses} ${className}`}>
          <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
          <span>Deficient (Resubmit)</span>
        </span>
      );
    case 'REJECTED':
      return (
        <span className={`inline-flex items-center rounded-full bg-slate-100 text-slate-700 border border-slate-300 ${sizeClasses} ${className}`}>
          <XCircle className="w-3.5 h-3.5 text-slate-500" />
          <span>Rejected</span>
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center rounded-full bg-slate-100 text-slate-600 border border-slate-200 ${sizeClasses} ${className}`}>
          <span>{status}</span>
        </span>
      );
  }
};
