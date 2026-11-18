export default function ProgressBar({ percent = 0 }) {
  const value = Math.max(0, Math.min(Number(percent) || 0, 100))
  const cls = value >= 100 ? 'danger' : value >= 80 ? 'warn' : 'ok'
  return (
    <div className="progress">
      <div className={`progress-fill ${cls}`} style={{ width: `${value}%` }} />
    </div>
  )
}
