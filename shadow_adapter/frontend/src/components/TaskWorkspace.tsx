import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  FileText,
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Download,
  File,
  ShieldCheck,
  Send,
  Loader2,
  Layers,
  ArrowLeft,
  Calendar,
  User,
  ExternalLink,
} from 'lucide-react';
import { ShadowTask } from '../types';
import { useSubmitTask } from '../hooks/useSubmitTask';

interface TaskWorkspaceProps {
  task: ShadowTask;
  onBack: () => void;
  onSubmittedSuccess?: () => void;
}

export const TaskWorkspace: React.FC<TaskWorkspaceProps> = ({
  task,
  onBack,
  onSubmittedSuccess,
}) => {
  const [deliverableText, setDeliverableText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { submitTask, submitting, error, isSuccess, successMessage } = useSubmitTask();

  // Extract upstream context and metadata
  const metadata = task.extra_metadata || {};
  const briefMarkdown =
    metadata.brief_md ||
    metadata.task_brief ||
    task.description ||
    `# Task Brief: ${task.title}\n\nExecute assigned task objective and submit deliverables below.`;
  const upstreamDeliverables = (metadata.upstream_deliverables as any[]) || [];
  const projectGoal = metadata.project_goal || metadata.goal || 'Execute OpenOPC agentic workflow step.';

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const addFiles = (newFiles: File[]) => {
    const combined = [...files, ...newFiles].slice(0, 5); // cap at 5
    setFiles(combined);
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const totalBytes = files.reduce((acc, f) => acc + f.size, 0);
  const totalMB = (totalBytes / (1024 * 1024)).toFixed(2);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await submitTask(task.id, deliverableText, files);
    if (res && onSubmittedSuccess) {
      onSubmittedSuccess();
    }
  };

  // Ghost Submission Success Screen (State Handoff)
  if (isSuccess) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-6">
        <div className="bg-opc-elevated border border-emerald-500/30 rounded-opc p-8 text-center shadow-opc-card space-y-6 animate-in fade-in duration-300">
          <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-opc-text tracking-tight">
              Deliverable Submitted
            </h2>
            <p className="text-emerald-400 font-semibold text-lg">
              The OpenOPC DAG has automatically resumed.
            </p>
            <p className="text-opc-text-secondary text-sm max-w-lg mx-auto">
              Your submission for task <code className="text-opc-accent font-mono">{task.title}</code> has been indexed into the corporate store and execution threads have unblocked.
            </p>
          </div>

          <div className="p-4 bg-opc-secondary border border-opc-border rounded-opc-sm text-left max-w-md mx-auto space-y-2 text-xs text-opc-text-dim font-mono">
            <div><span className="text-opc-text-secondary font-bold">Task ID:</span> {task.id}</div>
            <div><span className="text-opc-text-secondary font-bold">Work Item:</span> {task.opc_work_item_id || 'N/A'}</div>
            <div><span className="text-opc-text-secondary font-bold">Status:</span> Resumed (Phase.APPROVED)</div>
          </div>

          <div className="pt-4">
            <button
              onClick={onBack}
              className="px-6 py-2.5 bg-opc-secondary hover:bg-opc-border-hover border border-opc-border text-opc-text font-medium text-sm rounded-opc-sm transition-colors"
            >
              Return to Workspace Tasks
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-6 px-4 space-y-6">
      {/* Top Header Navigation */}
      <div className="flex items-center justify-between border-b border-opc-border pb-4">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-xs font-medium text-opc-text-secondary hover:text-opc-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Task List</span>
        </button>

        <div className="flex items-center space-x-3 text-xs text-opc-text-dim">
          <span className="flex items-center space-x-1">
            <Layers className="w-3.5 h-3.5 text-opc-accent" />
            <span>Project: <strong className="text-opc-text">{task.opc_project_id}</strong></span>
          </span>
          <span>•</span>
          <span className="flex items-center space-x-1">
            <User className="w-3.5 h-3.5 text-opc-accent" />
            <span>Role: <strong className="text-opc-text">{task.assigned_role || 'Unassigned'}</strong></span>
          </span>
        </div>
      </div>

      {/* Main Grid: Left = Context & Brief, Right = Deliverable Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Markdown Task Brief & Upstream Context */}
        <div className="lg:col-span-7 space-y-6">
          {/* Overarching Project Banner */}
          <div className="bg-opc-secondary/80 border border-opc-border rounded-opc p-4 space-y-1">
            <div className="flex items-center justify-between text-xs text-opc-accent font-semibold uppercase tracking-wider">
              <span>Overarching Goal</span>
              <span className="px-2 py-0.5 bg-opc-accent-soft rounded text-[10px]">Priority {task.priority}/10</span>
            </div>
            <p className="text-sm font-medium text-opc-text">{projectGoal}</p>
          </div>

          {/* Rendered Markdown Brief */}
          <div className="bg-opc-elevated border border-opc-border rounded-opc p-6 shadow-opc-card space-y-4">
            <div className="flex items-center justify-between border-b border-opc-border pb-3">
              <h2 className="text-base font-semibold text-opc-text flex items-center space-x-2">
                <FileText className="w-4 h-4 text-opc-accent" />
                <span>Task Specification & Brief</span>
              </h2>
              <span className="text-xs text-opc-text-dim">Markdown Rendered</span>
            </div>

            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{briefMarkdown}</ReactMarkdown>
            </div>
          </div>

          {/* Upstream Artifacts & Context Drawer */}
          {upstreamDeliverables.length > 0 && (
            <div className="bg-opc-elevated border border-opc-border rounded-opc p-6 shadow-opc-card space-y-4">
              <div className="flex items-center space-x-2 border-b border-opc-border pb-3">
                <Layers className="w-4 h-4 text-opc-indigo" />
                <h3 className="text-sm font-semibold text-opc-text">
                  Upstream Subagent Deliverables & Artifacts
                </h3>
              </div>

              <div className="space-y-4">
                {upstreamDeliverables.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-opc-secondary/90 border border-opc-border rounded-opc-sm p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between text-xs text-opc-text-secondary">
                      <span className="font-semibold text-opc-text">
                        [{item.role || 'Upstream Subagent'}]
                      </span>
                      <span className="font-mono text-[10px]">Task: {item.opc_task_id}</span>
                    </div>

                    <p className="text-xs text-opc-text-secondary whitespace-pre-wrap font-mono bg-opc-bg p-3 rounded border border-opc-border">
                      {item.deliverable_text || 'No text output.'}
                    </p>

                    {item.artifacts && item.artifacts.length > 0 && (
                      <div className="space-y-1.5 pt-1">
                        <div className="text-[11px] font-semibold text-opc-text-dim">
                          Attached Corporate Artifacts:
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {item.artifacts.map((art: any, aIdx: number) => (
                            <a
                              key={aIdx}
                              href={art.download_url || '#'}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center justify-between p-2 bg-opc-elevated border border-opc-border hover:border-opc-accent/50 rounded text-xs transition-colors group"
                            >
                              <div className="flex items-center space-x-2 truncate">
                                <File className="w-3.5 h-3.5 text-opc-accent shrink-0" />
                                <span className="truncate text-opc-text group-hover:text-opc-accent font-medium">
                                  {art.original_filename}
                                </span>
                              </div>
                              <Download className="w-3.5 h-3.5 text-opc-text-dim group-hover:text-opc-accent shrink-0 ml-2" />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (5 cols): The Deliverable Engine */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-opc-elevated border border-opc-border rounded-opc p-6 shadow-opc-card space-y-5 sticky top-20">
            <div className="flex items-center justify-between border-b border-opc-border pb-3">
              <h3 className="text-base font-semibold text-opc-text flex items-center space-x-2">
                <Send className="w-4 h-4 text-opc-accent" />
                <span>Deliverable Submission Engine</span>
              </h3>
              <span className="text-[11px] px-2 py-0.5 bg-opc-accent-soft text-opc-accent font-bold rounded">
                DAG Unblock Mode
              </span>
            </div>

            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-opc-sm text-xs text-rose-400 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Deliverable Notes Textarea */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-opc-text-secondary flex justify-between">
                  <span>Submission Summary & Code Notes</span>
                  <span className="text-opc-text-dim">{deliverableText.length} chars</span>
                </label>
                <textarea
                  value={deliverableText}
                  onChange={(e) => setDeliverableText(e.target.value)}
                  placeholder="Provide your solution summary, technical explanation, code snippet, or review feedback..."
                  rows={6}
                  className="w-full bg-opc-secondary border border-opc-border focus:border-opc-accent focus:ring-1 focus:ring-opc-accent text-opc-text placeholder-opc-text-dim text-xs rounded-opc-sm p-3 outline-none transition-all font-mono"
                  disabled={submitting}
                />
              </div>

              {/* Drag-and-Drop Deliverable Upload Zone */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-opc-text-secondary flex justify-between">
                  <span>Deliverable File Attachments</span>
                  <span className="text-opc-text-dim">{files.length}/5 Files ({totalMB} MB / 50MB)</span>
                </label>

                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-opc p-6 text-center cursor-pointer transition-colors ${
                    dragActive
                      ? 'border-opc-accent bg-opc-accent-soft/30'
                      : 'border-opc-border hover:border-opc-border-hover bg-opc-secondary/50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
                    className="hidden"
                    disabled={submitting}
                  />

                  <Upload className="w-6 h-6 text-opc-accent mx-auto mb-2" />
                  <p className="text-xs font-medium text-opc-text">
                    Drag and drop files here, or <span className="text-opc-accent underline">browse</span>
                  </p>
                  <p className="text-[10px] text-opc-text-dim mt-1">
                    Max 5 files, up to 10MB each (50MB payload cap)
                  </p>
                </div>

                {/* Selected File Chips */}
                {files.length > 0 && (
                  <div className="space-y-1.5 pt-2">
                    {files.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 bg-opc-secondary border border-opc-border rounded-opc-xs text-xs"
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <File className="w-3.5 h-3.5 text-opc-accent shrink-0" />
                          <span className="truncate text-opc-text font-medium">{file.name}</span>
                          <span className="text-[10px] text-opc-text-dim">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeFile(idx);
                          }}
                          className="text-opc-text-dim hover:text-rose-400 transition-colors p-1"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Submit Handoff Action Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 bg-opc-accent hover:bg-opc-accent-hover disabled:opacity-50 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-opc-sm transition-all shadow-opc-glow flex items-center justify-center space-x-2"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Resuming OpenOPC DAG...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Submit Deliverable & Resume DAG</span>
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center justify-center space-x-1 text-[10px] text-opc-text-dim text-center">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                <span>State transition automatically recorded with SHA-256 audit entry</span>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
