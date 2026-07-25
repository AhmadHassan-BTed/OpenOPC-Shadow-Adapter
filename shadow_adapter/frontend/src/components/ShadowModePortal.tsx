import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { ShadowTask, ContractorPublic } from '../types';
import { StatusBadge } from './StatusBadge';
import { FileUpload } from './FileUpload';

interface ShadowModePortalProps {
  initialTaskId?: string;
  onTaskSubmitted?: () => void;
}

export const ShadowModePortal: React.FC<ShadowModePortalProps> = ({
  initialTaskId,
  onTaskSubmitted,
}) => {
  const [user, setUser] = useState<ContractorPublic | null>(null);
  const [tasks, setTasks] = useState<ShadowTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(initialTaskId || null);
  const [selectedTask, setSelectedTask] = useState<ShadowTask | null>(null);

  const [deliverableText, setDeliverableText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadUserAndTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      loadTaskDetail(selectedTaskId);
    }
  }, [selectedTaskId]);

  const loadUserAndTasks = async () => {
    try {
      const me = await apiClient.getMe();
      setUser(me);

      const list = await apiClient.getTasks();
      setTasks(list);

      if (!selectedTaskId && list.length > 0) {
        setSelectedTaskId(list[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load portal data:', err);
    }
  };

  const loadTaskDetail = async (id: string) => {
    try {
      const task = await apiClient.getTask(id);
      setSelectedTask(task);
      setDeliverableText(task.deliverable_text || '');
    } catch (err: any) {
      console.error('Failed to load task detail:', err);
    }
  };

  const handleClaim = async () => {
    if (!selectedTaskId || !user) return;
    setIsClaiming(true);
    setStatusMsg(null);
    try {
      const updated = await apiClient.claimTask(selectedTaskId);
      setSelectedTask(updated);
      setStatusMsg({ type: 'success', text: `Task claimed successfully as ${user.username}.` });
      loadUserAndTasks();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to claim task.' });
    } finally {
      setIsClaiming(false);
    }
  };

  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTaskId) {
      setStatusMsg({ type: 'error', text: 'Please select a task.' });
      return;
    }
    if (!deliverableText.trim() && selectedFiles.length === 0) {
      setStatusMsg({ type: 'error', text: 'Deliverable notes or file upload required.' });
      return;
    }

    setIsSubmitting(true);
    setStatusMsg(null);

    try {
      await apiClient.submitTask(selectedTaskId, deliverableText, selectedFiles);
      setStatusMsg({
        type: 'success',
        text: 'Deliverable submitted successfully! OpenOPC DAG pipeline execution resumed.',
      });
      setDeliverableText('');
      setSelectedFiles([]);
      await loadUserAndTasks();
      if (selectedTaskId) {
        await loadTaskDetail(selectedTaskId);
      }
      if (onTaskSubmitted) {
        onTaskSubmitted();
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Submission failed.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto my-4 p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl text-slate-100 font-sans">
      {/* Portal Header */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-cyan-400 tracking-tight">
              Human Contractor Task Portal
            </h2>
            <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800/60 rounded">
              Shadow Mode active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Logged in as: <span className="text-slate-200 font-medium">{user?.display_name || user?.username || 'Contractor'}</span> | Roles:{' '}
            <span className="text-slate-300 font-mono text-[11px]">[{user?.roles.join(', ')}]</span>
          </p>
        </div>

        <button
          onClick={() => {
            apiClient.clearToken();
            window.location.reload();
          }}
          className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
        >
          Sign Out
        </button>
      </div>

      {/* Alert Banner */}
      {statusMsg && (
        <div
          className={`mt-4 p-3 rounded-lg text-sm border flex items-center justify-between ${
            statusMsg.type === 'error'
              ? 'bg-red-950/50 text-red-300 border-red-800/80'
              : 'bg-emerald-950/50 text-emerald-300 border-emerald-800/80'
          }`}
        >
          <span>{statusMsg.text}</span>
          <button
            onClick={() => setStatusMsg(null)}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Workspace Layout */}
      {tasks.length === 0 ? (
        <div className="my-10 p-8 bg-slate-950/60 border border-slate-800 text-center rounded-xl">
          <svg className="w-12 h-12 mx-auto text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-slate-300 text-sm font-semibold">No Pending Shadow Tasks</p>
          <p className="text-xs text-slate-500 mt-1">OpenOPC engine has not parked any tasks awaiting human deliverables yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          {/* Task Selection Sidebar */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Assigned Work Items ({tasks.length})
              </label>
              <button
                onClick={loadUserAndTasks}
                className="text-[11px] text-cyan-400 hover:text-cyan-300"
              >
                Refresh List
              </button>
            </div>

            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1 custom-scrollbar">
              {tasks.map((t) => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTaskId(t.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    t.id === selectedTaskId
                      ? 'bg-slate-800 border-cyan-500 text-cyan-100 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/30'
                      : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm truncate pr-2">{t.title}</span>
                    <StatusBadge status={t.status} />
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono truncate">
                    OPC: {t.opc_task_id}
                  </div>
                  {t.assigned_role && (
                    <div className="mt-2 text-[10px] text-slate-400 bg-slate-900 inline-block px-1.5 py-0.5 rounded border border-slate-800">
                      Role: {t.assigned_role}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Task Detail & Work Submission Form */}
          <div className="md:col-span-2 bg-slate-950/80 border border-slate-800 rounded-xl p-6 shadow-inner">
            {selectedTask ? (
              <div className="space-y-6">
                {/* Header info */}
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-bold text-slate-100">{selectedTask.title}</h3>
                    <StatusBadge status={selectedTask.status} />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400 mt-1 font-mono">
                    <span>Task ID: {selectedTask.id}</span>
                    <span>OPC Task: {selectedTask.opc_task_id}</span>
                  </div>
                  <div className="mt-3 p-3 bg-slate-900/90 border border-slate-800 rounded-lg text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                    {selectedTask.description || 'No description provided.'}
                  </div>
                </div>

                {/* Claiming Banner if Task is Pending */}
                {selectedTask.status === 'pending' && (
                  <div className="p-4 bg-amber-950/30 border border-amber-800/60 rounded-xl flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold text-amber-300">Task Unclaimed</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Claim this work item to lock it under your contractor account before submitting deliverables.
                      </p>
                    </div>
                    <button
                      onClick={handleClaim}
                      disabled={isClaiming}
                      className="px-4 py-2 text-xs font-semibold bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg shadow transition-colors shrink-0"
                    >
                      {isClaiming ? 'Claiming...' : 'Claim Task'}
                    </button>
                  </div>
                )}

                {/* Submission Form */}
                <form onSubmit={handleSubmitDeliverable} className="space-y-5 pt-2 border-t border-slate-800">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Deliverable Summary / Markdown Notes
                    </label>
                    <textarea
                      rows={5}
                      value={deliverableText}
                      onChange={(e) => setDeliverableText(e.target.value)}
                      placeholder="Describe the technical work performed, verification evidence, code changes, or compliance review notes..."
                      disabled={selectedTask.status !== 'claimed' || isSubmitting}
                      className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed font-mono leading-relaxed"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                      Attachment Deliverables (Max 5 files / 10MB per file)
                    </label>
                    <FileUpload
                      files={selectedFiles}
                      onFilesChange={setSelectedFiles}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={selectedTask.status !== 'claimed' || isSubmitting}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold text-sm rounded-lg shadow-lg shadow-emerald-950/40 transition-all flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span>Submitting Deliverable & Resuming DAG...</span>
                      </>
                    ) : (
                      <span>Submit Deliverable & Resume OpenOPC Pipeline</span>
                    )}
                  </button>
                </form>
              </div>
            ) : (
              <div className="text-slate-500 text-sm text-center py-12">
                Select a task from the left sidebar to view details and submit deliverables.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ShadowModePortal;
