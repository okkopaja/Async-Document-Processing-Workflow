import { DocumentStatus } from '@/types';

type StatusBadgeProps = {
  status: DocumentStatus;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span>{status}</span>;
}
