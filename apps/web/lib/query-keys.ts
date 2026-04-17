export const queryKeys = {
  documents: {
    all: ['documents'] as const,
    list: (params: Record<string, string | number | undefined>) => ['documents', params] as const,
    detail: (documentId: string) => ['documents', documentId] as const,
  },
  jobs: {
    detail: (jobId: string) => ['jobs', jobId] as const,
  },
};
