import { useCallback, useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import ProgressBar from '../components/ProgressBar'
import EmptyState from '../components/EmptyState'
import { formatMoney, currentMonth } from '../utils/format'

export default function BudgetsPage() {
  const [month, setMonth] = useState(currentMonth())
  const [budgets, setBudgets] = useState([])
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState({ category_id: '', limit_amount: '' })
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    api
      .get(`/budgets/status?month=${month}`)
      .then((items) => setBudgets(items || []))
      .catch(() => setBudgets([]))
  }, [month])

  useEffect(() => {
    api.get('/categories').then((c) => setCategories(c.filter((x) => x.type === 'expense'))).catch(() => {})
  }, [])

  useEffect(load, [load])

  const add = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post('/budgets', {
        category_id: Number(form.category_id),
        month,
        limit_amount: Number(form.limit_amount),
      })
      setNotice('Лимит сохранён')
      setForm({ category_id: '', limit_amount: '' })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (b) => {
    if (!window.confirm(`Удалить лимит по категории «${b.category_name}»?`)) return
    try {
      await api.del(`/budgets/${b.budget_id}`)
      setNotice('Лимит удалён')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const existingIds = new Set(budgets.map((b) => b.category_id))
  const notLimited = categories.filter((c) => !existingIds.has(c.id))

  return (
    <div>
      <PageHeader
        title="Бюджет на месяц"
        subtitle="Лимиты расходов по категориям и контроль исполнения"
        action={
          <div className="filter-item">
            Месяц
            <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
          </div>
        }
      />

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      <form className="card" onSubmit={add} style={{ marginBottom: 16 }}>
        <div className="card-title">Задать лимит</div>
        <div className="form-row">
          <div className="form-field">
            <label htmlFor="budget-cat">Категория расходов</label>
            <select
              id="budget-cat"
              value={form.category_id}
              onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
              required
            >
              <option value="">Выберите категорию</option>
              {notLimited.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="budget-limit">Лимит, ₽</label>
            <input
              id="budget-limit"
              type="number"
              min="0.01"
              step="0.01"
              value={form.limit_amount}
              onChange={(e) => setForm((f) => ({ ...f, limit_amount: e.target.value }))}
              placeholder="5000.00"
              required
            />
          </div>
        </div>
        <div className="modal-actions">
          <button type="submit" className="btn btn-primary" disabled={busy || notLimited.length === 0}>
            {busy ? 'Сохранение…' : 'Сохранить лимит'}
          </button>
        </div>
      </form>

      <div>
        {budgets.length === 0 ? (
          <EmptyState emoji="🎯" text="Лимиты на этот месяц не заданы" />
        ) : (
          budgets.map((b) => (
            <div key={b.budget_id} className="budget-row">
              <div className="budget-meta">
                <strong>{b.category_name}</strong>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <ProgressBar percent={b.percent} />
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: b.percent >= 100 ? '#dc2626' : b.percent >= 80 ? '#d97706' : '#0e9f6e',
                    }}
                  >
                    {b.percent}%
                  </span>
                </div>
              </div>
              <div className="budget-amounts">
                Потрачено: <strong>{formatMoney(b.spent)}</strong>
              </div>
              <div className="budget-amounts">
                Остаток: <strong>{formatMoney(b.remaining)}</strong>
              </div>
              <button type="button" className="btn btn-danger btn-sm" onClick={() => remove(b)}>
                🗑️
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
