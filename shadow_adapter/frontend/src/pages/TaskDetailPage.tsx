import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ContractorPublic, ShadowAuditEntry, ShadowTask } from '../types';
import { TaskWorkspace } from '../components/TaskWorkspace';
import { StatusBadge } from '../components/StatusBadge';
import { UserCheck, Shield, AlertCircle } from 'lucide-react';

interface TaskDetailPageProps {
  taskId: string;
  contractor: ContractorPublic;
  onBack: () => void;
}

export const TaskDetailPage: React.FC<TaskDetailPageProps> = ({ taskId, contractor, onBack }) => {
  const [task, setTask] = useState<ShadowTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const data = await api.getTask(taskId);
      setTask(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load task details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [taskId]);

  const handleClaim = async () => {
    try {
      setLoading(true);
      await api.claimTask(taskId);
      await fetchDetail();
    } catch (err: any) {
      setError(err.message || 'Failed to claim task');
      setLoading(false);
    }
  };

  const handleUnclaim = async () => {
    try {
      setLoading(true);
      await api.unclaimTask(taskId);
      await fetchDetail();
    } catch (err: any) {
      setError(err.message || 'Failed to unclaim task');
      setLoading(false);
    }
  };

  if (loading && !task) {
    return <div className="p-12 text-center text-opc-text-secondary text-sm">Loading task context...</div>;
  }

  if (!task) {
    return (
      <div className="max-w-xl mx-auto my-12 p-6 bg-rose-500/10 border border-rose-500/30 rounded-opc text-rose-400 text-sm space-y-4">
        <div className="flex items-center space-x-2 font-semibold">
          <AlertCircle className="w-5 h-5" />
          <span>Task Context Error</span>
        </div>
        <p>{error || 'Task not found or error loading context.'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-opc-secondary border border-opc-border text-opc-text rounded text-xs"
        >
          Back to Tasks
        </button>
      </div>
    );
  }

  const isClaimedByMe = task.assigned_contractor_id === contractor.id;
  const isClaimedByOther = Boolean(task.assigned_contractor_id && !isClaimedByMe);

  // If task is pending, prompt user to claim before entering workspace
  if (task.status === 'pending' && !isClaimedByMe) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-6">
        <div className="bg-opc-elevated border border-opc-border rounded-opc p-8 space-y-6 shadow-opc-card">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-opc-text">{task.title}</h2>
            <StatusBadge status={task.status} />
          </div>

          <p className="text-xs text-opc-text-secondary leading-relaxed">{task.description}</p>

          <div className="p-4 bg-opc-secondary border border-opc-border rounded-opc-sm space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-opc-text-dim">Assigned Role:</span>
              <span className="font-semibold text-opc-text">{task.assigned_role || 'Open to All'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-opc-text-dim">Project:</span>
              <span className="font-semibold text-opc-text">{task.opc_project_id}</span>
            </div>
          </div>

          {isClaimedByOther ? (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-opc-sm text-xs flex items-center space-x-2">
              <Shield className="w-4 h-4 shrink-0" />
              <span>This task is currently claimed by another worker.</span>
            </div>
          ) : (
            <div className="flex space-x-3 pt-2">
              <button
                onClick={handleClaim}
                className="flex-1 py-2.5 bg-opc-accent hover:bg-opc-accent-hover text-slate-950 font-bold text-xs rounded-opc-sm shadow-opc-glow flex items-center justify-center space-x-2 transition-all"
              >
                <UserCheck className="w-4 h-4" />
                <span>Claim Task Workspace</span>
              </button>
              <button
                onClick={onBack}
                className="px-5 py-2.5 bg-opc-secondary hover:bg-opc-border-hover border border-opc-border text-opc-text text-xs rounded-opc-sm"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Task claimed or in submission/resumed phase -> Render full TaskWorkspace
  return (
    <TaskWorkspace
      task={task}
      onBack={onBack}
      onSubmittedSuccess={() => fetchDetail()}
    />
  );
};
