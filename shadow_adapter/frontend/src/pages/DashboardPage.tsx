import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ContractorPublic, ShadowTask } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Clock, CheckCircle2, AlertTriangle, PlayCircle, Filter } from 'lucide-react';

interface DashboardPageProps {
  contractor: ContractorPublic;
  onSelectTask: (taskId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ contractor, onSelectTask }) => {
  const [tasks, setTasks] = useState<ShadowTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [onlyMine, setOnlyMine] = useState<boolean>(false);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const data = await api.getTasks({
        status: filterStatus === 'all' ? undefined : filterStatus,
        assigned_to_me: onlyMine,
      });
      setTasks(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [filterStatus, onlyMine]);

  const pendingCount = tasks.filter((t) => t.status === 'pending').length;
  const claimedCount = tasks.filter((t) => t.status === 'claimed').length;
  const resumedCount = tasks.filter((t) => t.status === 'resumed').length;
  const failedCount = tasks.filter((t) => t.status === 'failed').length;

  return (
    <div className="space-y-6">
      {/* Header Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-opc-elevated border border-opc-border rounded-opc flex items-center justify-between">
          <div>
            <p className="text-xs text-opc-text-secondary font-medium">Pending Claim</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{pendingCount}</p>
          </div>
          <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-opc-sm">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 bg-opc-elevated border border-opc-border rounded-opc flex items-center justify-between">
          <div>
            <p className="text-xs text-opc-text-secondary font-medium">In Progress (Claimed)</p>
            <p className="text-2xl font-bold text-indigo-400 mt-1">{claimedCount}</p>
          </div>
          <div className="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-opc-sm">
            <PlayCircle className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 bg-opc-elevated border border-opc-border rounded-opc flex items-center justify-between">
          <div>
            <p className="text-xs text-opc-text-secondary font-medium">Resumed to OpenOPC</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{resumedCount}</p>
          </div>
          <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-opc-sm">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 bg-opc-elevated border border-opc-border rounded-opc flex items-center justify-between">
          <div>
            <p className="text-xs text-opc-text-secondary font-medium">Failed / Escalated</p>
            <p className="text-2xl font-bold text-rose-400 mt-1">{failedCount}</p>
          </div>
          <div className="p-2.5 bg-rose-500/10 text-rose-400 rounded-opc-sm">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-opc-elevated border border-opc-border rounded-opc">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-opc-accent" />
          <span className="text-xs font-semibold text-opc-text">Filter Queue:</span>
          <div className="flex space-x-1 pl-2">
            {['all', 'pending', 'claimed', 'submitted', 'resumed', 'failed'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1 text-xs rounded-full capitalize transition-colors ${
                  filterStatus === st
                    ? 'bg-opc-accent text-white font-medium'
                    : 'bg-opc-secondary text-opc-text-secondary hover:text-opc-text'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        <label className="flex items-center space-x-2 text-xs text-opc-text cursor-pointer">
          <input
            type="checkbox"
            checked={onlyMine}
            onChange={(e) => setOnlyMine(e.target.checked)}
            className="rounded border-opc-border bg-opc-secondary text-opc-accent focus:ring-opc-accent"
          />
          <span>Only my claimed tasks</span>
        </label>
      </div>

      {/* Task Queue Table */}
      {error ? (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-opc text-rose-400 text-sm">
          {error}
        </div>
      ) : loading ? (
        <div className="p-12 text-center text-opc-text-secondary text-sm">Loading task queue...</div>
      ) : tasks.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-opc-border rounded-opc bg-opc-surface text-opc-text-dim text-sm">
          No parked tasks match the selected filters.
        </div>
      ) : (
        <div className="bg-opc-elevated border border-opc-border rounded-opc overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-opc-secondary text-opc-text-secondary uppercase tracking-wider font-semibold border-b border-opc-border">
              <tr>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Task Title</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Parked At</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-opc-border">
              {tasks.map((task) => (
                <tr
                  key={task.id}
                  onClick={() => onSelectTask(task.id)}
                  className="hover:bg-opc-secondary/50 cursor-pointer transition-colors"
                >
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="py-3.5 px-4 font-medium text-opc-text max-w-md truncate">
                    {task.title}
                    {task.opc_work_item_id && (
                      <span className="ml-2 text-[10px] text-opc-text-dim">({task.opc_work_item_id.slice(0, 8)})</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-opc-text-secondary">{task.assigned_role || 'Unassigned'}</td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-opc-surface text-opc-text font-mono text-[10px]">
                      P{task.priority}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-opc-text-dim whitespace-nowrap">
                    {new Date(task.parked_at).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTask(task.id);
                      }}
                      className="px-3 py-1 bg-opc-accent/15 text-opc-accent hover:bg-opc-accent hover:text-white rounded-opc-sm text-xs font-medium transition-colors"
                    >
                      View Detail →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
