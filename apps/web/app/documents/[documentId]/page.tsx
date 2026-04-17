'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { DocumentDetailResponse, DocumentStatus } from '@/types';
import { useDocumentProgress } from '@/hooks/useDocumentProgress';
import { getApiUrl } from '@/lib/endpoints';
import styles from './document-detail.module.css';

interface DocumentDetailPageProps {
  params: Promise<{ documentId: string }>;
}

type ReviewDocument = DocumentDetailResponse['document'];
type ReviewResult = NonNullable<DocumentDetailResponse['result']>;

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const router = useRouter();
  const { documentId } = use(params);
  const normalizedDocumentId =
    documentId && documentId !== 'undefined' && documentId !== 'null'
      ? documentId
      : null;
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live progress updates via WebSocket
  const progress = useDocumentProgress(normalizedDocumentId);

  // Fetch document detail
  useEffect(() => {
    if (!normalizedDocumentId) {
      setLoading(false);
      setDetail(null);
      setError('Invalid document id');
      return;
    }

    let isMounted = true;
    let isRequestInFlight = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    let activeController: AbortController | null = null;

    const fetchDetail = async () => {
      if (!isMounted || isRequestInFlight) {
        return;
      }

      isRequestInFlight = true;
      activeController = new AbortController();

      try {
        if (isMounted) {
          setLoading(true);
        }
        const response = await fetch(getApiUrl(`/api/documents/${normalizedDocumentId}`), {
          signal: activeController.signal,
        });
        if (!response.ok) {
          throw new Error(`Failed to fetch document: ${response.statusText}`);
        }
        const data: DocumentDetailResponse = await response.json();
        if (isMounted) {
          setDetail(data);
          setError(null);
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }

        const message = err instanceof Error ? err.message : String(err);
        if (isMounted) {
          setError(message);
        }
      } finally {
        isRequestInFlight = false;
        activeController = null;
        if (isMounted) {
          setLoading(false);
        }

        if (isMounted) {
          pollTimer = setTimeout(fetchDetail, 3000);
        }
      }
    };

    fetchDetail();

    return () => {
      isMounted = false;
      activeController?.abort();
      if (pollTimer) {
        clearTimeout(pollTimer);
      }
    };
  }, [normalizedDocumentId]);

  const refreshDetail = async () => {
    if (!normalizedDocumentId) {
      return;
    }

    try {
      const response = await fetch(getApiUrl(`/api/documents/${normalizedDocumentId}`));
      if (!response.ok) {
        throw new Error(`Failed to fetch document: ${response.statusText}`);
      }
      const data: DocumentDetailResponse = await response.json();
      setDetail(data);
      setError(null);
    } catch (err) {
      console.error('Failed to refresh:', err);
    }
  };

  const displayDetail =
    progress.latestEvent && detail
      ? {
          ...detail,
          document: {
            ...detail.document,
            status: progress.latestEvent.status,
          },
          job: detail.job
            ? {
                ...detail.job,
                status: progress.latestEvent.status,
                currentStage: progress.latestEvent.stage,
                progressPercent: progress.latestEvent.progressPercent,
              }
            : null,
        }
      : detail;

  if (loading && !displayDetail) {
    return (
      <main className={styles.container}>
        <p>Loading document details...</p>
      </main>
    );
  }

  if (error && !displayDetail) {
    return (
      <main className={styles.container}>
        <div className={styles.error}>{error}</div>
        <Link href="/">← Back to Dashboard</Link>
      </main>
    );
  }

  if (!displayDetail) {
    return (
      <main className={styles.container}>
        <p>Document not found</p>
        <Link href="/">← Back to Dashboard</Link>
      </main>
    );
  }

  const { document, job, result, events } = displayDetail;
  const canEdit = result && !result.isFinalized;
  const canFinalize = document.status === 'COMPLETED' && result && !result.isFinalized;

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1>{document.originalFilename}</h1>
          <p className={styles.subtitle}>Document ID: {document.id}</p>
        </div>
        <Link href="/" className={styles.backLink}>
          ← Back to Dashboard
        </Link>
      </header>

      <div className={styles.grid}>
        {/* Metadata Card */}
        <section className={styles.card}>
          <h2>Metadata</h2>
          <dl className={styles.metadata}>
            <dt>Filename:</dt>
            <dd>{document.originalFilename}</dd>
            <dt>Type:</dt>
            <dd>{document.mimeType}</dd>
            <dt>Size:</dt>
            <dd>{formatBytes(document.sizeBytes)}</dd>
            <dt>Uploaded:</dt>
            <dd>{formatDate(document.createdAt)}</dd>
            <dt>Status:</dt>
            <dd>
              <span
                className={styles.statusBadge}
                style={{ backgroundColor: getStatusColor(document.status) }}
              >
                {document.status}
              </span>
            </dd>
          </dl>
        </section>

        {/* Processing Status Card */}
        {job && (
          <section className={styles.card}>
            <h2>Processing Status</h2>
            <dl className={styles.metadata}>
              <dt>Job Status:</dt>
              <dd>
                <span
                  className={styles.statusBadge}
                  style={{ backgroundColor: getStatusColor(job.status) }}
                >
                  {job.status}
                </span>
              </dd>
              <dt>Current Stage:</dt>
              <dd>{job.currentStage || '—'}</dd>
              <dt>Progress:</dt>
              <dd>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${job.progressPercent}%` }}
                  />
                </div>
                <span>{job.progressPercent}%</span>
              </dd>
              <dt>Attempts:</dt>
              <dd>{job.attemptNumber}</dd>
              {job.errorMessage && (
                <>
                  <dt>Error:</dt>
                  <dd className={styles.error}>{job.errorMessage}</dd>
                </>
              )}
            </dl>
          </section>
        )}
      </div>

      {/* Event Timeline */}
      {events.length > 0 && (
        <section className={styles.card}>
          <h2>Processing Timeline</h2>
          <div className={styles.timeline}>
            {events.map((evt) => (
              <div key={evt.id} className={styles.timelineItem}>
                <div className={styles.timelineDot} />
                <div className={styles.timelineContent}>
                  <p className={styles.timelineEvent}>{evt.eventType}</p>
                  <p className={styles.timelineTime}>{formatDate(evt.createdAt)}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Review Form */}
      {result && canEdit && (
        <ReviewFormSection
          document={document}
          result={result}
          onUpdate={refreshDetail}
        />
      )}

      {/* Actions */}
      {result && canFinalize && (
        <section className={styles.card}>
          <h2>Actions</h2>
          <FinalizeButton
            documentId={documentId}
            version={result.version}
            onFinalize={refreshDetail}
          />
        </section>
      )}

      {result?.isFinalized && (
        <section className={styles.card}>
          <h2>Actions</h2>
          <p className={styles.info}>This document is finalized and locked.</p>
        </section>
      )}

      <section className={styles.card}>
        <h2>Danger Zone</h2>
        <DeleteDocumentButton
          documentId={document.id}
          filename={document.originalFilename}
          onDeleted={() => {
            router.push('/');
            router.refresh();
          }}
        />
      </section>
    </main>
  );
}

/**
 * Review Form Component
 */
interface ReviewFormSectionProps {
  document: ReviewDocument;
  result: ReviewResult;
  onUpdate: () => void;
}

function ReviewFormSection({
  document,
  result,
  onUpdate,
}: ReviewFormSectionProps) {
  const [title, setTitle] = useState(result.title || '');
  const [category, setCategory] = useState(result.category || '');
  const [summary, setSummary] = useState(result.summary || '');
  const [keywords, setKeywords] = useState((result.keywords || []).join(', '));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch(getApiUrl(`/api/documents/${document.id}/result`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title || undefined,
          category: category || undefined,
          summary: summary || undefined,
          keywords: keywords ? keywords.split(',').map((k) => k.trim()) : [],
          version: result.version,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error?.message || 'Failed to update result');
      }

      setSuccess(true);
      onUpdate();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={styles.card}>
      <h2>Review & Edit</h2>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formGroup}>
          <label htmlFor="title">Title</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Document title"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="category">Category</label>
          <input
            id="category"
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Document category"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="summary">Summary</label>
          <textarea
            id="summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Brief summary of content"
            rows={4}
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="keywords">Keywords (comma-separated)</label>
          <input
            id="keywords"
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="keyword1, keyword2, keyword3"
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}
        {success && <div className={styles.success}>Updated successfully!</div>}

        <button type="submit" disabled={loading} className={styles.submitButton}>
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </section>
  );
}

/**
 * Finalize Button Component
 */
interface FinalizeButtonProps {
  documentId: string;
  version: number;
  onFinalize: () => void;
}

function FinalizeButton({
  documentId,
  version,
  onFinalize,
}: FinalizeButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFinalize = async () => {
    if (!window.confirm('Finalize this document? This action cannot be undone.')) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(getApiUrl(`/api/documents/${documentId}/finalize`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error?.message || 'Failed to finalize');
      }

      onFinalize();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {error && <div className={styles.error}>{error}</div>}
      <button
        onClick={handleFinalize}
        disabled={loading}
        className={styles.finalizeButton}
      >
        {loading ? 'Finalizing...' : '✓ Finalize Document'}
      </button>
      <p className={styles.info}>
        Finalizing locks the document for export. You cannot edit it after this action.
      </p>
    </div>
  );
}

interface DeleteDocumentButtonProps {
  documentId: string;
  filename: string;
  onDeleted: () => void;
}

function DeleteDocumentButton({
  documentId,
  filename,
  onDeleted,
}: DeleteDocumentButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (
      !window.confirm(
        `Delete ${filename}? This will remove the document, jobs, events, results, and uploaded files.`
      )
    ) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(getApiUrl(`/api/documents/${documentId}`), {
        method: 'DELETE',
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(err?.error?.message || 'Failed to delete document');
      }

      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {error && <div className={styles.error}>{error}</div>}
      <button
        onClick={handleDelete}
        disabled={loading}
        className={styles.deleteButton}
      >
        {loading ? 'Deleting...' : 'Delete Document'}
      </button>
      <p className={styles.warningText}>
        This permanently deletes this document and all related processing artifacts.
      </p>
    </div>
  );
}

// Helper functions
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}

function getStatusColor(status: DocumentStatus | string): string {
  switch (status) {
    case 'QUEUED':
      return '#999';
    case 'PROCESSING':
      return '#2196F3';
    case 'COMPLETED':
      return '#4CAF50';
    case 'FAILED':
      return '#F44336';
    case 'FINALIZED':
      return '#009688';
    default:
      return '#999';
  }
}
