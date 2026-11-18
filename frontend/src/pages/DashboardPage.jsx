import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import ProgressBar from '../components/ProgressBar'
import EmptyState from '../components/EmptyState'
import { formatMoney, formatDate, currentMonth } from '../utils/format'

export default function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [budgets, setBudgets] = useState([])
  const [recent, setRecent] = useState([])
  const [goals, setGoals] = useState([])
  const [error, setError] = useState('')

  const load = () => {
    const month = currentMonth()
    Promise.all([
      api.get('/analytics/summary'),
      api.get(`/budgets/status?month=${month}`),
      api.get('/operations?limit=6'),
      api.get('/goals'),
    ])
      .then(([s, b, ops, g]) => {
        setSummary(s)
        setBudgets(b)
        setRecent(ops.items || [])
        setGoals(g)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  return (
    <div>
      <PageHeader
        title="Дашборд"
        subtitle={`Сводка за всё время · ${new Date().toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}`}
      />

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card stat-income">
          <div className="stat-label">Доходы</div>
          <div className="stat-value">{summary ? formatMoney(summary.income) : '…'}</div>
          <div className="stat-hint">{summary ? `${summary.operations_count} операций всего` : ''}</div>
        </div>
        <div className="stat-card stat-expense">
          <div className="stat-label">Расходы</div>
          <div className="stat-value">{summary ? formatMoney(summary.expense) : '…'}</div>
          <div className="stat-hint">
            {summary && summary.top_categories.length > 0
              ? `Больше всего: ${summary.top_categories[0].category_name}`
              : ''}
          </div>
        </div>
        <div className="stat-card stat-balance">
          <div className="stat-label">Баланс</div>
          <div className="stat-value">
            {summary ? `${summary.balance >= 0 ? '+' : '−'}${formatMoney(Math.abs(summary.balance))}` : '…'}
          </div>
          <div className="stat-hint">{summary && summary.balance >= 0 ? 'Положительный итог' : 'Расходы выше доходов'}</div>
        </div>
      </div>

      <div className="dash-cols">
        <div className="card">
          <div className="card-title">Последние операции</div>
          {recent.length === 0 ? (
            <EmptyState emoji="🗒️" text="Операций пока нет. Добавьте первую!" />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Категория</th>
                    <th>Комментарий</th>
                    <th>Сумма</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((op) => (
                    <tr key={op.id}>
                      <td>{formatDate(op.date)}</td>
                      <td>{op.category_name || 'Без категории'}</td>
                      <td>{op.comment || '—'}</td>
                      <td className={op.type === 'income' ? 'amount-income' : 'amount-expense'}>
                        {op.type === 'income' ? '+' : '−'}
                        {formatMoney(op.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ marginTop: 14 }}>
            <Link className="btn btn-secondary btn-sm" to="/operations">
              Все операции →
            </Link>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Бюджет на месяц · {currentMonth()}</div>
          {budgets.length === 0 ? (
            <EmptyState emoji="🎯" text="Бюджет не задан. Настройте лимиты на месяц." />
          ) : (
            budgets.map((b) => (
              <div key={b.budget_id} style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 6 }}>
                  <strong>{b.category_name}</strong>
                  <span style={{ color: '#6b7280' }}>
                    {formatMoney(b.spent)} / {formatMoney(b.limit_amount)}
                  </span>
                </div>
                <ProgressBar percent={b.percent} />
                <small style={{ color: '#6b7280' }}>
                  {b.percent}% лимита · осталось {formatMoney(b.remaining)}
                </small>
              </div>
            ))
          )}
          <div style={{ marginTop: 10 }}>
            <Link className="btn btn-secondary btn-sm" to="/budgets">
              Управление бюджетом →
            </Link>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Мои мечты</div>
        {goals.length === 0 ? (
          <EmptyState emoji="💎" text="Мечты пока не созданы. Начните копить на что-то важное!" />
        ) : (
          goals.slice(0, 3).map((g) => (
            <div key={g.id} className="goal-item">
              <div>
                <div className="goal-head">
                  <span className="goal-name">{g.name}</span>
                  {g.deadline && <span className="goal-deadline">до {formatDate(g.deadline)}</span>}
                </div>
                <div className="goal-progress-text">
                  {formatMoney(g.saved_amount)} из {formatMoney(g.target_amount)} · {g.progress_percent}%
                </div>
                <ProgressBar percent={g.progress_percent} />
              </div>
              <Link className="btn btn-secondary btn-sm" to="/goals">
                Детали
              </Link>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
