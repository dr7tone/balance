export default function EmptyState({ emoji = '📭', text = 'Здесь пока пусто' }) {
  return (
    <div className="empty-state">
      <span className="empty-emoji">{emoji}</span>
      <p>{text}</p>
    </div>
  )
}
