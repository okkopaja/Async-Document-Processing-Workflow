'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getApiUrl } from '@/lib/endpoints';

const ALLOWED_EXTENSIONS = ['txt', 'md', 'pdf', 'docx', 'csv'];
const MAX_FILE_SIZE_MB = 50; // Max upload size
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

interface UploadError {
  file: string;
  message: string;
}

function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
}

function validateFile(file: File): UploadError | null {
  // Check file size
  if (file.size === 0) {
    return { file: file.name, message: 'File is empty' };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      file: file.name,
      message: `File exceeds ${MAX_FILE_SIZE_MB}MB limit`,
    };
  }

  // Check file extension
  const ext = getFileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      file: file.name,
      message: `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
    };
  }

  return null;
}

export function UploadForm() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<UploadError[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const newFiles = Array.from(files);

    // Validate files
    const validationErrors: UploadError[] = [];
    const validFiles: File[] = [];

    for (const file of newFiles) {
      const error = validateFile(file);
      if (error) {
        validationErrors.push(error);
      } else {
        validFiles.push(file);
      }
    }

    setErrors(validationErrors);
    setSelectedFiles(prev => [...prev, ...validFiles]);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedFiles.length === 0) {
      setErrors([{ file: 'form', message: 'Please select at least one file' }]);
      return;
    }

    setIsLoading(true);
    setErrors([]);

    try {
      const formData = new FormData();

      // Submit from selected state so drag-drop and browse behave identically.
      for (const file of selectedFiles) {
        formData.append('files', file, file.name);
      }

      const response = await fetch(getApiUrl('/api/documents/upload'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        setErrors([{
          file: 'form',
          message: errorData.error?.message || 'Upload failed',
        }]);
        return;
      }

      await response.json();
      
      // Clear form and redirect to dashboard
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Redirect to dashboard to see uploaded documents
      router.push('/');
    } catch (err) {
      setErrors([{
        file: 'form',
        message: err instanceof Error ? err.message : 'Upload failed',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const submitLabel = isLoading
    ? 'Uploading...'
    : selectedFiles.length > 0
      ? `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`
      : 'Upload Files';

  return (
    <div className='upload-form-container'>
      <form onSubmit={handleSubmit} className='upload-form' suppressHydrationWarning>
        {/* Drag and drop area */}
        <div
          className={`drag-drop-area ${isDragActive ? 'active' : ''}`}
          onClick={() => {
            if (!isLoading) {
              fileInputRef.current?.click();
            }
          }}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type='file'
            multiple
            accept={ALLOWED_EXTENSIONS.map(ext => `.${ext}`).join(',')}
            onChange={(e) => {
              handleFileSelect(e.target.files);
              e.currentTarget.value = '';
            }}
            className='file-input'
            disabled={isLoading}
            suppressHydrationWarning
          />
          <div className='drag-drop-content'>
            <svg className='upload-icon' viewBox='0 0 24 24' fill='none' stroke='currentColor'>
              <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3v-7' />
            </svg>
            <p className='drag-drop-text'>
              Drag files here or <span className='click-text'>click to browse</span>
            </p>
            <p className='drag-drop-hint'>
              Supported: {ALLOWED_EXTENSIONS.join(', ')} (max {MAX_FILE_SIZE_MB}MB each)
            </p>
          </div>
        </div>

        {/* File preview list */}
        {selectedFiles.length > 0 && (
          <div className='file-preview-list'>
            <h3>Selected Files ({selectedFiles.length})</h3>
            {selectedFiles.map((file, index) => (
              <div key={`${file.name}-${file.size}-${index}`} className='file-preview-item'>
                <div className='file-info'>
                  <span className='file-name'>{file.name}</span>
                  <span className='file-size'>{formatFileSize(file.size)}</span>
                </div>
                <button
                  type='button'
                  onClick={() => removeFile(index)}
                  className='remove-btn'
                  disabled={isLoading}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Errors */}
        {errors.length > 0 && (
          <div className='error-messages'>
            {errors.map((error, index) => (
              <div key={`${error.file}-${error.message}-${index}`} className='error-message'>
                {error.file !== 'form' && <strong>{error.file}:</strong>}
                {' '}{error.message}
              </div>
            ))}
          </div>
        )}

        {/* Submit button */}
        <button
          type='submit'
          className='submit-btn'
          disabled={selectedFiles.length === 0 || isLoading}
          suppressHydrationWarning
        >
          {submitLabel}
        </button>
      </form>

      <style jsx>{`
        .upload-form-container {
          padding: 2rem;
        }

        .upload-form {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .drag-drop-area {
          border: 2px dashed #ccc;
          border-radius: 8px;
          padding: 3rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          background: #fafafa;
        }

        .drag-drop-area:hover {
          border-color: #999;
          background: #f5f5f5;
        }

        .drag-drop-area.active {
          border-color: #0066cc;
          background: #e6f0ff;
        }

        .file-input {
          display: none;
        }

        .drag-drop-content {
          pointer-events: none;
        }

        .upload-icon {
          width: 48px;
          height: 48px;
          margin: 0 auto 1rem;
          color: #666;
        }

        .drag-drop-text {
          font-size: 1.1rem;
          margin: 0.5rem 0;
          color: #333;
        }

        .click-text {
          color: #0066cc;
          font-weight: 500;
        }

        .drag-drop-hint {
          font-size: 0.875rem;
          color: #666;
          margin: 0.5rem 0 0;
        }

        .file-preview-list {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 1rem;
          background: #fafafa;
        }

        .file-preview-list h3 {
          margin: 0 0 1rem 0;
          font-size: 1rem;
        }

        .file-preview-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          background: white;
          border-radius: 6px;
          margin-bottom: 0.5rem;
          border: 1px solid #e0e0e0;
        }

        .file-preview-item:last-child {
          margin-bottom: 0;
        }

        .file-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          flex: 1;
        }

        .file-name {
          font-weight: 500;
          color: #333;
        }

        .file-size {
          font-size: 0.875rem;
          color: #999;
        }

        .remove-btn {
          background: none;
          border: none;
          color: #999;
          cursor: pointer;
          font-size: 1.2rem;
          padding: 0.25rem 0.5rem;
          transition: color 0.2s;
        }

        .remove-btn:hover:not(:disabled) {
          color: #d32f2f;
        }

        .remove-btn:disabled {
          cursor: not-allowed;
          opacity: 0.5;
        }

        .error-messages {
          border: 1px solid #ffebee;
          border-radius: 8px;
          padding: 1rem;
          background: #ffebee;
        }

        .error-message {
          color: #d32f2f;
          font-size: 0.95rem;
          margin-bottom: 0.5rem;
        }

        .error-message:last-child {
          margin-bottom: 0;
        }

        .submit-btn {
          padding: 0.75rem 1.5rem;
          background: #0066cc;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .submit-btn:hover:not(:disabled) {
          background: #0052a3;
        }

        .submit-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
