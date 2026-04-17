const DEFAULT_ALLOWED_EXTENSIONS = ['txt', 'md', 'pdf', 'docx', 'csv'];

export function isAllowedExtension(filename: string, allowed = DEFAULT_ALLOWED_EXTENSIONS): boolean {
  const extension = filename.split('.').pop()?.toLowerCase();
  return Boolean(extension && allowed.includes(extension));
}

export function validateFileSize(sizeBytes: number, maxMb = 25): boolean {
  return sizeBytes > 0 && sizeBytes <= maxMb * 1024 * 1024;
}
