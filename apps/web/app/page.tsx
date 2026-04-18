'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DocumentStatus } from '@/types';
import { useJobProgress } from '@/hooks/useJobProgress';
import { getApiUrl } from '@/lib/endpoints';
import styles from './dashboard.module.css';

interface DocumentListItem {
	documentId: string;
	originalFilename: string;
	mimeType: string;
	sizeBytes: number;
	status: DocumentStatus;
	createdAt: string;
	latestJobId?: string | null;
	progressPercent?: number | null;
	currentStage?: string | null;
}

interface PaginatedResponse<T> {
	items: T[];
	page: number;
	pageSize: number;
	total: number;
}

/**
 * Dashboard page with live document processing progress.
 *
 * Features:
 * - Real-time progress updates via WebSocket
 * - Status badges and progress bars
 * - Connection status indicator
 * - Fallback to REST API if WebSocket is down
 */
export default function DashboardPage() {
	const [documents, setDocuments] = useState<DocumentListItem[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);
	const [deleteError, setDeleteError] = useState<string | null>(null);

	useEffect(() => {
		let isMounted = true;
		let isRequestInFlight = false;
		let hasCompletedInitialFetch = false;
		let pollTimer: ReturnType<typeof setTimeout> | null = null;
		let activeController: AbortController | null = null;

		const fetchDocuments = async () => {
			if (!isMounted || isRequestInFlight) {
				return;
			}

			isRequestInFlight = true;
			activeController = new AbortController();

			try {
				// Show full-page loading state only for the first fetch.
				if (isMounted && !hasCompletedInitialFetch) {
					setLoading(true);
				}
				const response = await fetch(getApiUrl('/api/documents?page=1&page_size=50'), {
					signal: activeController.signal,
				});
				if (!response.ok) {
					throw new Error(`Failed to fetch documents: ${response.statusText}`);
				}
				const data: PaginatedResponse<DocumentListItem> = await response.json();
				if (isMounted) {
					setDocuments(data.items);
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
				console.error('Failed to fetch documents:', message);
			} finally {
				isRequestInFlight = false;
				activeController = null;
				if (isMounted && !hasCompletedInitialFetch) {
					setLoading(false);
					hasCompletedInitialFetch = true;
				}

				if (isMounted) {
					pollTimer = setTimeout(fetchDocuments, 5000);
				}
			}
		};

		fetchDocuments();

		return () => {
			isMounted = false;
			activeController?.abort();
			if (pollTimer) {
				clearTimeout(pollTimer);
			}
		};
	}, []);

	const handleDeleteDocument = async (documentId: string, filename: string) => {
		if (
			!window.confirm(
				`Delete ${filename}? This will remove the document and all related processing data.`
			)
		) {
			return;
		}

		setDeletingDocumentId(documentId);
		setDeleteError(null);

		try {
			const response = await fetch(getApiUrl(`/api/documents/${documentId}`), {
				method: 'DELETE',
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => null);
				throw new Error(errorData?.error?.message || 'Failed to delete document');
			}

			setDocuments((previous) => previous.filter((doc) => doc.documentId !== documentId));
		} catch (err) {
			setDeleteError(err instanceof Error ? err.message : String(err));
		} finally {
			setDeletingDocumentId(null);
		}
	};

	if (loading && documents.length === 0) {
		return (
			<main className={styles.dashboard}>
				<h1>Async Document Processing Dashboard</h1>
				<p className={styles.loading}>Loading documents...</p>
			</main>
		);
	}

	return (
		<main className={styles.dashboard}>
			<header className={styles.header}>
				<h1>Async Document Processing Dashboard</h1>
				<Link className={styles.uploadButton} href='/upload'>
					+ Upload Documents
				</Link>
			</header>

			{error && (
				<div className={styles.error}>
					<p>Error: {error}</p>
				</div>
			)}

			{deleteError && (
				<div className={styles.error}>
					<p>Error: {deleteError}</p>
				</div>
			)}

			{documents.length === 0 ? (
				<div className={styles.empty}>
					<p>No documents yet. Get started by uploading your first document.</p>
					<Link className={styles.uploadButtonLarge} href='/upload'>
						Upload Your First Document
					</Link>
				</div>
			) : (
				<div className={styles.container}>
					<table className={styles.table}>
						<thead>
							<tr>
								<th>Filename</th>
								<th>Type</th>
								<th>Size</th>
								<th>Status</th>
								<th>Progress</th>
								<th>Current Stage</th>
								<th>Created</th>
								<th>Actions</th>
							</tr>
						</thead>
						<tbody>
							{documents.map((document) => (
								<DashboardDocumentRow
									key={document.documentId}
									document={document}
									onDelete={handleDeleteDocument}
									isDeleting={deletingDocumentId === document.documentId}
								/>
							))}
						</tbody>
					</table>
				</div>
			)}
		</main>
	);
}

function DashboardDocumentRow({
	document,
	onDelete,
	isDeleting,
}: {
	document: DocumentListItem;
	onDelete: (documentId: string, filename: string) => Promise<void>;
	isDeleting: boolean;
}) {
	const progress = useJobProgress(document.latestJobId ?? null);
	const latestEvent = progress.latestEvent;
	const status = (latestEvent?.status as DocumentStatus) ?? document.status;
	const progressPercent = latestEvent?.progressPercent ?? document.progressPercent;
	const currentStage = latestEvent?.stage ?? document.currentStage;
	const isSynced = Boolean(latestEvent);

	return (
		<tr className={styles.row}>
			<td className={styles.filename}>{document.originalFilename}</td>
			<td>{document.mimeType}</td>
			<td>{formatBytes(document.sizeBytes)}</td>
			<td>
				<span
					className={styles.badge}
					style={{
						backgroundColor: getStatusColor(status),
					}}
				>
					{status}
				</span>
				{isSynced && (
					<span className={styles.syncBadge} title='Live update via WebSocket'>
						●
					</span>
				)}
			</td>
			<td className={styles.progress}>
				{progressPercent !== undefined && progressPercent !== null && (
					<>
						<div className={styles.progressBar}>
							<div
								className={styles.progressFill}
								style={{ width: `${progressPercent}%` }}
							/>
						</div>
						<span className={styles.progressText}>{progressPercent}%</span>
					</>
				)}
			</td>
			<td className={styles.stage}>{currentStage || '—'}</td>
			<td className={styles.date}>{formatDate(document.createdAt)}</td>
			<td>
				<div className={styles.actions}>
					<Link className={styles.link} href={`/documents/${document.documentId}`}>
						View
					</Link>
					<button
						type='button'
						className={styles.deleteButton}
						onClick={() => onDelete(document.documentId, document.originalFilename)}
						disabled={isDeleting}
					>
						{isDeleting ? 'Deleting...' : 'Delete'}
					</button>
				</div>
			</td>
		</tr>
	);
}

function formatBytes(bytes: number): string {
	if (bytes === 0) return '0 Bytes';
	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`;
}

function formatDate(dateString: string): string {
	return new Date(dateString).toLocaleString();
}

function getStatusColor(status: DocumentStatus): string {
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
