type ProgressBarProps = {
  value: number;
};

export function ProgressBar({ value }: ProgressBarProps) {
  return <progress max={100} value={Math.max(0, Math.min(100, value))} />;
}
