import React from 'react';
import { ShadowTaskStatus } from '../types';

interface StatusBadgeProps {
  status: ShadowTaskStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case 'pending':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'claimed':
        return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
      case 'submitted':
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'resumed':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'failed':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'cancelled':
        return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
      default:
        return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider ${getBadgeStyle()}`}
    >
      {status}
    </span>
  );
};
