import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ContractorPublic, ShadowAuditEntry, ShadowTask } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { FileUpload } from '../components/FileUpload';
import { ArrowLeft, CheckCircle2, UserCheck, Send, AlertCircle, FileText, Activity } from 'lucide-react';

interface TaskDetailPageProps {
  taskId: string;
  contractor: ContractorPublic;
  onBack: () => void;
}

export const TaskDetailPage: React.FC<TaskDetailPageProps> = ({ taskId, contractor, onBack }) => {
  const [task, setTask] = useState<ShadowTask | null>(null);
  const [auditLog, setAuditLog] = useState<ShadowAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Submission Form State
  const [deliverableText, setDeliverableText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const data = await api.getTask(taskId);
      setTask(data);
      const auditData = await api.getAuditLog(taskId);
      setAuditLog(auditData);
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

  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!deliverableText.trim() && files.length === 0) {
      setError('Please provide deliverable text or attach at least one file.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await api.submitTask(taskId, deliverableText, files);
      setSubmitSuccess(res.message);
      await fetchDetail();
    } catch (err: any) {
      setError(err.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !task) {
    return <div className="p-12 text-center text-opc-text-secondary">Loading task context...</div>;
  }

  if (!task) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-opc text-rose-400">
        Task not found or error loading context: {error}
      </div>
    );
  }

  const isClaimedByMe = task.assigned_contractor_id === contractor.id;
  const isClaimedByOther = task.assigned_contractor_id && !isClaimedByMe;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center space-x-1.5 text-xs text-opc-text-secondary hover:text-opc-accent transition-colors font-medium"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Queue</span>
      </button>

      {/* Task Header Card */}
      <div className="p-6 bg-opc-elevated border border-opc-border rounded-opc space-y-4 shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1 max-w-2xl">
            <div className="flex items-center space-x-3">
              <StatusBadge status={task.status} />
              <span className="text-xs text-opc-text-dim">OPC Task ID: {task.opc_task_id}</span>
            </div>
            <h2 className="text-xl font-bold text-opc-text tracking-tight pt-1">{task.title}</h2>
          </div>

          <div className="flex items-center space-x-3">
            {task.status === 'pending' && (
              <button
                onClick={handleClaim}
                className="px-4 py-2 bg-opc-accent hover:bg-opc-accent-hover text-white text-xs font-semibold rounded-opc-sm transition-colors shadow-lg shadow-opc-accent/20 flex items-center space-x-1.5"
              >
                <UserCheck className="w-4 h-4" />
                <span>Claim Task</span>
              </button>
            )}

            {task.status === 'claimed' && isClaimedByMe && (
              <button
                onClick={handleUnclaim}
                className="px-3 py-1.5 bg-opc-secondary border border-opc-border text-opc-text-secondary hover:text-rose-400 rounded-opc-sm text-xs font-medium transition-colors"
              >
                Release Claim
              </button>
            )}
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-3 bg-opc-secondary/50 rounded-opc-sm text-xs border border-opc-border/50">
          <div>
            <span className="text-opc-text-dim block text-[10px] uppercase font-semibold">Assigned Role</span>
            <span className="font-medium text-opc-text">{task.assigned_role || 'Unassigned'}</span>
          </div>
          <div>
            <span className="text-opc-text-dim block text-[10px] uppercase font-semibold">Priority</span>
            <span className="font-medium text-opc-text">Priority {task.priority}</span>
          </div>
          <div>
            <span className="text-opc-text-dim block text-[10px] uppercase font-semibold">Parked At</span>
            <span className="font-medium text-opc-text">{new Date(task.parked_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-opc-text-dim block text-[10px] uppercase font-semibold">Work Item ID</span>
            <span className="font-medium text-opc-text">{task.opc_work_item_id || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Task Description / Prompt */}
      <div className="p-6 bg-opc-elevated border border-opc-border rounded-opc space-y-3">
        <h3 className="text-xs font-semibold text-opc-text-secondary uppercase tracking-wider flex items-center space-x-2">
          <FileText className="w-4 h-4 text-opc-accent" />
          <span>Task Brief & Description</span>
        </h3>
        <div className="p-4 bg-opc-bg border border-opc-border rounded-opc-sm text-xs text-opc-text font-mono whitespace-pre-wrap leading-relaxed">
          {task.description || 'No description provided.'}
        </div>
      </div>

      {/* Submission Form (If Claimed By Me) */}
      {task.status === 'claimed' && isClaimedByMe && (
        <form
          onSubmit={handleSubmitDeliverable}
          className="p-6 bg-opc-elevated border-2 border-opc-accent/30 rounded-opc space-y-5 shadow-2xl"
        >
          <div className="flex items-center justify-between border-b border-opc-border pb-3">
            <h3 className="text-sm font-bold text-opc-text flex items-center space-x-2">
              <Send className="w-4 h-4 text-opc-accent" />
              <span>Submit Deliverable to OpenOPC</span>
            </h3>
            <span className="text-[10px] px-2 py-0.5 bg-opc-accent-soft text-opc-accent rounded font-medium">
              Ready for Submission
            </span>
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-opc-sm text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-opc-text-secondary mb-1.5">
              Deliverable Summary / Text Report
            </label>
            <textarea
              rows={5}
              value={deliverableText}
              onChange={(e) => setDeliverableText(e.target.value)}
              placeholder="Provide a detailed summary of the work completed, findings, or notes for the DAG..."
              className="w-full p-3 bg-opc-secondary border border-opc-border rounded-opc-sm text-xs text-opc-text placeholder:text-opc-text-dim focus:outline-none focus:border-opc-accent font-mono transition-colors"
            />
          </div>

          {/* Browser Limit Enforced Multi-File Upload Component */}
          <FileUpload
            files={files}
            onFilesChange={setFiles}
            maxFiles={5}
            maxFileSizeMb={10}
            maxTotalSizeMb={50}
          />

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded-opc-sm transition-colors shadow-lg shadow-emerald-500/20 flex items-center space-x-2 disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{submitting ? 'Submitting & Resuming DAG...' : 'Submit Deliverable & Resume DAG'}</span>
            </button>
          </div>
        </form>
      )}

      {/* Submitted / Resumed Output Display */}
      {(task.status === 'submitted' || task.status === 'resumed') && (
        <div className="p-6 bg-emerald-500/10 border border-emerald-500/30 rounded-opc space-y-4">
          <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
            <CheckCircle2 className="w-5 h-5" />
            <span>Deliverable Submitted — OpenOPC DAG Resumed</span>
          </div>

          {task.deliverable_text && (
            <div className="space-y-1">
              <span className="text-[10px] text-opc-text-dim uppercase font-semibold">Deliverable Report</span>
              <div className="p-3 bg-opc-bg border border-opc-border rounded-opc-sm text-xs text-opc-text font-mono whitespace-pre-wrap">
                {task.deliverable_text}
              </div>
            </div>
          )}

          {task.deliverable_files.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] text-opc-text-dim uppercase font-semibold">Uploaded Files</span>
              <div className="flex flex-wrap gap-2">
                {task.deliverable_files.map((file, i) => (
                  <div
                    key={i}
                    className="px-3 py-1.5 bg-opc-secondary border border-opc-border rounded-opc-sm text-xs text-opc-text font-mono"
                  >
                    {file}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Audit Log Timeline */}
      <div className="p-6 bg-opc-elevated border border-opc-border rounded-opc space-y-3">
        <h3 className="text-xs font-semibold text-opc-text-secondary uppercase tracking-wider flex items-center space-x-2">
          <Activity className="w-4 h-4 text-opc-accent" />
          <span>Audit Log Timeline</span>
        </h3>

        <div className="space-y-2 pt-1">
          {auditLog.map((log) => (
            <div
              key={log.id}
              className="flex items-center justify-between p-2.5 bg-opc-secondary/50 border border-opc-border/40 rounded-opc-sm text-xs"
            >
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-opc-accent shrink-0" />
                <span className="font-semibold uppercase text-opc-text text-[10px]">{log.action}</span>
                {log.actor_id && <span className="text-opc-text-dim text-[10px]">(Actor: {log.actor_id.slice(0, 8)})</span>}
              </div>
              <span className="text-[10px] text-opc-text-dim">{new Date(log.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
