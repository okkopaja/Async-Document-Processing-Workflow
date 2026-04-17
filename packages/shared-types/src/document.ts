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
