/**
 * ProgressBar — accessible upload/processing progress indicator.
 *
 * Props:
 * - value: 0–100 (percentage), or null for indeterminate
 * - label: Accessible label for the progress bar
 * - className: Additional CSS classes
 */
interface ProgressBarProps {
  value: number | null
  label?: string
  className?: string
}

export default function ProgressBar({ value, label = 'Loading…', className = '' }: ProgressBarProps) {
  const isIndeterminate = value === null

  return (
    <div className={`space-y-1 ${className}`} role="status" aria-label={label}>
      <div className="flex justify-between text-xs text-gray-400">
        <span>{label}</span>
        {!isIndeterminate && <span>{Math.round(value!)}%</span>}
      </div>
      <div
        role="progressbar"
        aria-valuenow={isIndeterminate ? undefined : value!}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
        className="h-2 bg-gray-700 rounded-full overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-all duration-300
            ${isIndeterminate
              ? 'w-1/3 bg-violet-500 animate-[slide_1.5s_ease-in-out_infinite]'
              : 'bg-violet-500'
            }`}
          style={!isIndeterminate ? { width: `${value}%` } : undefined}
        />
      </div>
    </div>
  )
}
