export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString();
}

export function formatDate(isoDate: string): string {
  return formatDateTime(isoDate);
}
