'use client';

import { useState } from 'react';
import { getApiUrl } from '@/lib/endpoints';

interface ActionBarProps {
  documentId: string;
  jobId?: string;
  status: string;
  isFinalized: boolean;
  onRetrySuccess?: () => void;
}

export function ActionBar({ documentId, jobId, status, isFinalized, onRetrySuccess }: ActionBarProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const canRetry = status === 'FAILED' && jobId;
  const canExport = isFinalized;

  const handleRetry = async () => {
    if (!jobId) return;

    setIsRetrying(true);
    setRetryError(null);

    try {
      const response = await fetch(getApiUrl(`/api/jobs/${jobId}/retry`), {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'Failed to retry job');
      }

      // Success - refresh the current view or hand control back to the parent.
      if (onRetrySuccess) {
        onRetrySuccess();
      } else {
        window.location.reload();
      }
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : 'Failed to retry job');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleExportJson = async () => {
    try {
      const response = await fetch(
        getApiUrl(`/api/exports/documents/${documentId}/export.json`)
      );
      if (!response.ok) {
        throw new Error('Failed to export JSON');
      }
      const data = await response.json();
      
      // Create blob and download
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${documentId}-export.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export JSON failed:', err);
      alert(err instanceof Error ? err.message : 'Export failed');
    }
  };

  const handleExportCsv = async () => {
    try {
      const response = await fetch(
        getApiUrl(`/api/exports/documents/${documentId}/export.csv`)
      );
      if (!response.ok) {
        throw new Error('Failed to export CSV');
      }
      const data = await response.json();
      
      // Create blob and download
      const blob = new Blob([data.csv_data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${documentId}-export.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export CSV failed:', err);
      alert(err instanceof Error ? err.message : 'Export failed');
    }
  };

  if (!canRetry && !canExport) {
    return null;
  }

  return (
    <div className='action-bar'>
      <div className='action-buttons'>
        {canRetry && (
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className='retry-btn'
            title='Retry failed job'
          >
            {isRetrying ? 'Retrying...' : 'Retry'}
          </button>
        )}
        
        {canExport && (
          <>
            <button
              onClick={handleExportJson}
              className='export-btn'
              title='Export as JSON'
            >
              Export JSON
            </button>
            <button
              onClick={handleExportCsv}
              className='export-btn'
              title='Export as CSV'
            >
              Export CSV
            </button>
          </>
        )}
      </div>

      {retryError && (
        <div className='error-message'>
          {retryError}
        </div>
      )}

      <style jsx>{`
        .action-bar {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .action-buttons {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .retry-btn,
        .export-btn {
          padding: 0.5rem 1rem;
          border: 1px solid #ccc;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          font-size: 0.95rem;
          transition: all 0.2s;
        }

        .retry-btn {
          background: #ff9800;
          color: white;
          border-color: #ff9800;
        }

        .retry-btn:hover:not(:disabled) {
          background: #f57c00;
          border-color: #f57c00;
        }

        .export-btn {
          background: #0066cc;
          color: white;
          border-color: #0066cc;
        }

        .export-btn:hover:not(:disabled) {
          background: #0052a3;
          border-color: #0052a3;
        }

        .retry-btn:disabled,
        .export-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .error-message {
          padding: 0.75rem;
          background: #ffebee;
          color: #d32f2f;
          border-radius: 4px;
          font-size: 0.95rem;
        }
      `}</style>
    </div>
  );
}
