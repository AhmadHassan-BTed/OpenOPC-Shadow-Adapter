import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ContractorPublic, ShadowTask } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ShadowModePortal } from '../components/ShadowModePortal';
import { Clock, CheckCircle2, AlertTriangle, PlayCircle, Filter, LayoutGrid, UserCheck } from 'lucide-react';

interface DashboardPageProps {
  contractor: ContractorPublic;
  onSelectTask: (taskId: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ contractor, onSelectTask }) => {
  const [activeTab, setActiveTab] = useState<'queue' | 'portal'>('queue');
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
      {/* Top View Toggle Tabs */}
      <div className="flex items-center justify-between border-b border-opc-border pb-3">
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab('queue')}
            className={`flex items-center space-x-2 px-4 py-2 text-xs font-medium rounded-opc-sm transition-colors ${
              activeTab === 'queue'
                ? 'bg-opc-accent/15 text-opc-accent border border-opc-accent/30'
                : 'text-opc-text-secondary hover:text-opc-text hover:bg-opc-elevated'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
            <span>Task Queue & Analytics</span>
          </button>
          <button
            onClick={() => setActiveTab('portal')}
            className={`flex items-center space-x-2 px-4 py-2 text-xs font-medium rounded-opc-sm transition-colors ${
              activeTab === 'portal'
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-opc-text-secondary hover:text-opc-text hover:bg-opc-elevated'
            }`}
          >
            <UserCheck className="w-4 h-4" />
            <span>Shadow Mode Portal (Contractor)</span>
          </button>
        </div>
      </div>

      {activeTab === 'portal' ? (
        <ShadowModePortal onTaskSubmitted={fetchTasks} />
      ) : (
        <>
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
                        ? 'bg-opc-accent text-slate-950 font-semibold'
                        : 'bg-opc-card text-opc-text-secondary hover:text-opc-text'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <label className="flex items-center space-x-2 text-xs text-opc-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={onlyMine}
                onChange={(e) => setOnlyMine(e.target.checked)}
                className="rounded border-opc-border text-opc-accent focus:ring-0 bg-opc-card"
              />
              <span>Assigned to Me Only</span>
            </label>
          </div>

          {/* Task List Table */}
          {loading ? (
            <div className="p-12 text-center text-xs text-opc-text-secondary">Loading shadow tasks...</div>
          ) : error ? (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-opc text-xs">{error}</div>
          ) : tasks.length === 0 ? (
            <div className="p-12 bg-opc-elevated border border-opc-border rounded-opc text-center">
              <p className="text-sm font-semibold text-opc-text">No Shadow Tasks Found</p>
              <p className="text-xs text-opc-text-secondary mt-1">Adjust filters or launch OpenOPC tasks assigned to Shadow mode.</p>
            </div>
          ) : (
            <div className="bg-opc-elevated border border-opc-border rounded-opc overflow-hidden">
              <table className="w-full text-left text-xs text-opc-text">
                <thead className="bg-opc-card text-opc-text-secondary font-medium uppercase text-[10px] tracking-wider border-b border-opc-border">
                  <tr>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Task Title</th>
                    <th className="p-3.5">OPC Task ID</th>
                    <th className="p-3.5">Role</th>
                    <th className="p-3.5">Contractor</th>
                    <th className="p-3.5">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-opc-border">
                  {tasks.map((task) => (
                    <tr key={task.id} className="hover:bg-opc-card/50 transition-colors">
                      <td className="p-3.5">
                        <StatusBadge status={task.status} />
                      </td>
                      <td className="p-3.5 font-medium text-opc-text">{task.title}</td>
                      <td className="p-3.5 font-mono text-opc-text-secondary text-[11px]">{task.opc_task_id}</td>
                      <td className="p-3.5 text-opc-text-secondary">{task.assigned_role || '-'}</td>
                      <td className="p-3.5 font-mono text-opc-text-secondary text-[11px]">
                        {task.assigned_contractor_id || 'Unassigned'}
                      </td>
                      <td className="p-3.5">
                        <button
                          onClick={() => onSelectTask(task.id)}
                          className="px-3 py-1 bg-opc-accent/10 hover:bg-opc-accent/20 text-opc-accent font-semibold rounded text-xs transition-colors"
                        >
                          View & Submit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default DashboardPage;
