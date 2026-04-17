import type { DocumentStatus, JobStage } from './document';

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
