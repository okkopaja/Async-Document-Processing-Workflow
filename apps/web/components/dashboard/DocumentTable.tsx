'use client';

import Link from 'next/link';
import { useState } from 'react';
import { DocumentListItem } from '@/types';
import { formatBytes, formatDate } from '@/lib/formatters';
import { getApiUrl } from '@/lib/endpoints';

interface DocumentTableProps {
  documents: DocumentListItem[];
  onRefresh?: () => void;
}

export function DocumentTable({ documents, onRefresh }: DocumentTableProps) {
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const handleRetry = async (jobId: string) => {
    setRetryingJobId(jobId);
    setRetryError(null);

    try {
      const response = await fetch(getApiUrl(`/api/jobs/${jobId}/retry`), {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'Failed to retry job');
      }

      // Refresh the table
      if (onRefresh) {
        onRefresh();
      } else {
        window.location.reload();
      }
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : 'Failed to retry job');
    } finally {
      setRetryingJobId(null);
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      QUEUED: '#ff9800',
      PROCESSING: '#2196f3',
      COMPLETED: '#4caf50',
      FAILED: '#f44336',
      FINALIZED: '#4caf50',
    };
    return colors[status] || '#999';
  };

  if (documents.length === 0) {
    return (
      <div className='empty-state'>
        <p>No documents found. <Link href="/upload">Upload some documents</Link> to get started.</p>
        <style jsx>{`
          .empty-state {
            text-align: center;
            padding: 2rem;
            color: #999;
          }

          .empty-state a {
            color: #0066cc;
            text-decoration: none;
          }

          .empty-state a:hover {
            text-decoration: underline;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className='table-container'>
      <table className='documents-table'>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Size</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id}>
              <td>
                <Link href={`/documents/${doc.id}`} className='filename-link'>
                  {doc.originalFilename}
                </Link>
              </td>
              <td>
                <span
                  className='status-badge'
                  style={{ backgroundColor: getStatusColor(doc.status) }}
                >
                  {doc.status}
                </span>
              </td>
              <td>
                <div className='progress-cell'>
                  <div className='progress-bar'>
                    <div
                      className='progress-fill'
                      style={{ width: `${doc.progressPercent}%` }}
                    />
                  </div>
                  <span className='progress-text'>{doc.progressPercent}%</span>
                </div>
              </td>
              <td className='size'>{formatBytes(doc.sizeBytes)}</td>
              <td className='date'>{formatDate(doc.createdAt)}</td>
              <td className='actions'>
                {doc.status === 'FAILED' && doc.latestJobId && (
                  <button
                    className='retry-btn'
                    onClick={() => handleRetry(doc.latestJobId!)}
                    disabled={retryingJobId === doc.latestJobId}
                    title='Retry failed job'
                  >
                    {retryingJobId === doc.latestJobId ? '⟳' : 'Retry'}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {retryError && (
        <div className='retry-error'>
          {retryError}
          <button onClick={() => setRetryError(null)} className='close-btn'>
            ✕
          </button>
        </div>
      )}

      <style jsx>{`
        .table-container {
          overflow-x: auto;
          margin-top: 1.5rem;
        }

        .documents-table {
          width: 100%;
          border-collapse: collapse;
          background: white;
          border-radius: 4px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        thead {
          background: #f5f5f5;
          border-bottom: 2px solid #e0e0e0;
        }

        th {
          padding: 1rem;
          text-align: left;
          font-weight: 600;
          color: #333;
          font-size: 0.95rem;
        }

        td {
          padding: 1rem;
          border-bottom: 1px solid #e0e0e0;
        }

        tbody tr:hover {
          background: #fafafa;
        }

        tbody tr:last-child td {
          border-bottom: none;
        }

        .filename-link {
          color: #0066cc;
          text-decoration: none;
          font-weight: 500;
        }

        .filename-link:hover {
          text-decoration: underline;
        }

        .status-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          color: white;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .progress-cell {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .progress-bar {
          flex: 1;
          min-width: 80px;
          height: 6px;
          background: #e0e0e0;
          border-radius: 3px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: #4caf50;
          transition: width 0.2s;
        }

        .progress-text {
          min-width: 35px;
          text-align: right;
          font-size: 0.9rem;
          color: #666;
        }

        .size,
        .date {
          color: #666;
          font-size: 0.95rem;
          white-space: nowrap;
        }

        .actions {
          text-align: center;
        }

        .retry-btn {
          padding: 0.4rem 0.8rem;
          background: #ff9800;
          color: white;
          border: none;
          border-radius: 3px;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          transition: all 0.2s;
        }

        .retry-btn:hover:not(:disabled) {
          background: #f57c00;
          transform: translateY(-1px);
        }

        .retry-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .retry-error {
          margin-top: 1rem;
          padding: 0.75rem;
          background: #ffebee;
          color: #d32f2f;
          border-radius: 4px;
          font-size: 0.95rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .close-btn {
          background: none;
          border: none;
          color: #d32f2f;
          cursor: pointer;
          font-size: 1.2rem;
        }
      `}</style>
    </div>
  );
}
