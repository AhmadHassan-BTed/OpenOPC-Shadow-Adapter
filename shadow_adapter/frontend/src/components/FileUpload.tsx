import React, { useState } from 'react';
import { Upload, X, FileText, AlertCircle } from 'lucide-react';

interface FileUploadProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  maxFiles?: number;
  maxFileSizeMb?: number;
  maxTotalSizeMb?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  files,
  onFilesChange,
  maxFiles = 5,
  maxFileSizeMb = 10,
  maxTotalSizeMb = 50,
}) => {
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (!e.target.files) return;

    const selectedFiles = Array.from(e.target.files);
    const newFilesList = [...files, ...selectedFiles];

    // 1. Enforce max file count limit (max 5)
    if (newFilesList.length > maxFiles) {
      setError(`Maximum ${maxFiles} files per submission allowed.`);
      return;
    }

    // 2. Enforce single file size limit (max 10MB)
    const maxSingleBytes = maxFileSizeMb * 1024 * 1024;
    for (const f of selectedFiles) {
      if (f.size > maxSingleBytes) {
        setError(`File '${f.name}' exceeds the maximum single file size of ${maxFileSizeMb}MB.`);
        return;
      }
    }

    // 3. Enforce total payload size limit (max 50MB)
    const maxTotalBytes = maxTotalSizeMb * 1024 * 1024;
    const totalBytes = newFilesList.reduce((acc, f) => acc + f.size, 0);
    if (totalBytes > maxTotalBytes) {
      setError(`Total payload size exceeds the maximum limit of ${maxTotalSizeMb}MB.`);
      return;
    }

    onFilesChange(newFilesList);
  };

  const removeFile = (index: number) => {
    setError(null);
    const updated = files.filter((_, i) => i !== index);
    onFilesChange(updated);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const totalSize = files.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-opc-text-secondary">
        <span className="font-medium text-opc-text">Attachments (Deliverables)</span>
        <span>
          {files.length} / {maxFiles} files ({formatSize(totalSize)} / {maxTotalSizeMb}MB)
        </span>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-opc-sm text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {files.length < maxFiles && (
        <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-opc-border hover:border-opc-accent/50 bg-opc-surface hover:bg-opc-elevated rounded-opc cursor-pointer transition-colors group">
          <div className="flex flex-col items-center justify-center pt-1 pb-2">
            <Upload className="w-6 h-6 mb-2 text-opc-text-secondary group-hover:text-opc-accent transition-colors" />
            <p className="mb-1 text-xs text-opc-text font-medium">
              <span className="text-opc-accent">Click to upload</span> or drag and drop
            </p>
            <p className="text-[10px] text-opc-text-dim">
              Max {maxFiles} files • Up to {maxFileSizeMb}MB per file • Total max {maxTotalSizeMb}MB
            </p>
          </div>
          <input
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.png,.jpg,.jpeg,.zip,.tar.gz"
          />
        </label>
      )}

      {files.length > 0 && (
        <div className="space-y-1.5">
          {files.map((file, idx) => (
            <div
              key={`${file.name}-${idx}`}
              className="flex items-center justify-between p-2.5 bg-opc-elevated border border-opc-border rounded-opc-sm text-xs"
            >
              <div className="flex items-center space-x-2 truncate">
                <FileText className="w-4 h-4 text-opc-accent shrink-0" />
                <span className="truncate text-opc-text font-medium">{file.name}</span>
                <span className="text-[10px] text-opc-text-dim">({formatSize(file.size)})</span>
              </div>
              <button
                type="button"
                onClick={() => removeFile(idx)}
                className="text-opc-text-dim hover:text-rose-400 p-1 rounded transition-colors"
                title="Remove file"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
