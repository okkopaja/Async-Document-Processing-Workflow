export type DocumentStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'FINALIZED';

export type JobStage =
  | 'document_received'
  | 'job_queued'
  | 'job_started'
  | 'document_parsing_started'
  | 'document_parsing_completed'
  | 'field_extraction_started'
  | 'field_extraction_completed'
  | 'result_persist_started'
  | 'result_persist_completed'
  | 'job_completed'
  | 'job_failed'
  | 'job_retry_scheduled';

export interface ProgressEvent {
  eventId: string;
  jobId: string;
  documentId: string;
  status: DocumentStatus;
  stage: JobStage;
  progressPercent: number;
  message: string;
  attemptNumber: number;
  timestamp: string;
}

export interface DocumentListItem {
  id: string;
  originalFilename: string;
  mimeType: string;
  sizeBytes: number;
  status: DocumentStatus;
  createdAt: string;
  latestJobId?: string | null;
  progressPercent: number;
  currentStage?: JobStage | null;
  attemptNumber?: number;
  errorMessage?: string | null;
}

export interface DocumentDetail {
  id: string;
  originalFilename: string;
  storedFilename: string;
  mimeType: string;
  extension: string;
  sizeBytes: number;
  storagePath: string;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
  latestJobId: string | null;
}

export interface JobDetail {
  id: string;
  documentId: string;
  celeryTaskId: string | null;
  status: DocumentStatus;
  currentStage: JobStage | null;
  progressPercent: number;
  attemptNumber: number;
  errorCode: string | null;
  errorMessage: string | null;
  queuedAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentResult {
  id: string;
  documentId: string;
  title: string | null;
  category: string | null;
  summary: string | null;
  keywords: string[];
  rawText: string | null;
  structuredJson: Record<string, unknown>;
  isFinalized: boolean;
  finalizedAt: string | null;
  createdAt: string;
  updatedAt: string;
  version: number;
}

export interface JobEvent {
  id: string;
  jobId: string;
  eventType: string;
  payloadJson: Record<string, unknown> | null;
  createdAt: string;
}

export interface DocumentDetailResponse {
  document: DocumentDetail;
  job: JobDetail | null;
  result: DocumentResult | null;
  events: JobEvent[];
}
