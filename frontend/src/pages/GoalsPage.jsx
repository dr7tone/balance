import { useCallback, useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import Modal from '../components/Modal'
import ProgressBar from '../components/ProgressBar'
import EmptyState from '../components/EmptyState'
import { formatMoney, formatDate } from '../utils/format'

export default function GoalsPage() {
  const [goals, setGoals] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [contributeGoal, setContributeGoal] = useState(null)
  const [busy, setBusy] = useState(false)

  const [goalForm, setGoalForm] = useState({ name: '', target_amount: '', deadline: '' })
  const [contribForm, setContribForm] = useState({ amount: '', note: '' })

  const load = useCallback(() => {
    api.get('/goals').then(setGoals).catch(() => setGoals([]))
  }, [])

  useEffect(load, [load])

  const addGoal = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post('/goals', {
        name: goalForm.name.trim(),
        target_amount: Number(goalForm.target_amount),
        deadline: goalForm.deadline || null,
      })
      setNotice('Новая мечта создана!')
      setGoalForm({ name: '', target_amount: '', deadline: '' })
      setAddOpen(false)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const contribute = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post(`/goals/${contributeGoal.id}/contribute`, {
        amount: Number(contribForm.amount),
        note: contribForm.note,
      })
      setNotice(`Вклад в «${contributeGoal.name}» засчитан (расход «Накопления» создан автоматически)`)
      setContribForm({ amount: '', note: '' })
      setContributeGoal(null)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (g) => {
    if (!window.confirm(`Удалить мечту «${g.name}»?`)) return
    try {
      await api.del(`/goals/${g.id}`)
      setNotice('Мечта удалена')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <PageHeader
        title="Мечты"
        subtitle="Накопление на цели: вклады фиксируются как расход «Накопления»"
        action={
          <button type="button" className="btn btn-primary" onClick={() => setAddOpen(true)}>
            + Новая мечта
          </button>
        }
      />

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {goals.length === 0 ? (
        <EmptyState emoji="💎" text="Мечты пока не созданы. Начните копить!" />
      ) : (
        <div className="card">
          {goals.map((g) => (
            <div key={g.id} className="goal-item">
              <div>
                <div className="goal-head">
                  <span className="goal-name">{g.name}</span>
                  {g.deadline && <span className="goal-deadline">до {formatDate(g.deadline)}</span>}
                </div>
                <div className="goal-progress-text">
                  {formatMoney(g.saved_amount)} из {formatMoney(g.target_amount)} · {g.progress_percent}%
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <ProgressBar percent={g.progress_percent} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignSelf: 'center' }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setContributeGoal(g)}
                  disabled={g.progress_percent >= 100}
                >
                  {g.progress_percent >= 100 ? 'Достигнута 🎉' : 'Пополнить'}
                </button>
                <button type="button" className="btn btn-danger btn-sm" onClick={() => remove(g)}>
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {addOpen && (
        <Modal title="Новая мечта" onClose={() => setAddOpen(false)}>
          <form onSubmit={addGoal}>
            <div className="form-field">
              <label htmlFor="goal-name">Что копим?</label>
              <input
                id="goal-name"
                value={goalForm.name}
                onChange={(e) => setGoalForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Например: новый ноутбук"
                maxLength={200}
                required
              />
            </div>
            <div className="form-row" style={{ marginTop: 14 }}>
              <div className="form-field">
                <label htmlFor="goal-target">Целевая сумма, ₽</label>
                <input
                  id="goal-target"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={goalForm.target_amount}
                  onChange={(e) => setGoalForm((f) => ({ ...f, target_amount: e.target.value }))}
                  placeholder="80000.00"
                  required
                />
              </div>
              <div className="form-field">
                <label htmlFor="goal-deadline">Срок (необязательно)</label>
                <input
                  id="goal-deadline"
                  type="date"
                  value={goalForm.deadline}
                  onChange={(e) => setGoalForm((f) => ({ ...f, deadline: e.target.value }))}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setAddOpen(false)}>
                Отмена
              </button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Сохранение…' : 'Создать'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {contributeGoal && (
        <Modal title={`Пополнить: ${contributeGoal.name}`} onClose={() => setContributeGoal(null)}>
          <form onSubmit={contribute}>
            <div className="form-field">
              <label htmlFor="contrib-amount">Сумма вклада, ₽</label>
              <input
                id="contrib-amount"
                type="number"
                min="0.01"
                step="0.01"
                value={contribForm.amount}
                onChange={(e) => setContribForm((f) => ({ ...f, amount: e.target.value }))}
                placeholder="15000.00"
                required
                autoFocus
              />
            </div>
            <div className="form-field" style={{ marginTop: 14 }}>
              <label htmlFor="contrib-note">Заметка (необязательно)</label>
              <input
                id="contrib-note"
                value={contribForm.note}
                onChange={(e) => setContribForm((f) => ({ ...f, note: e.target.value }))}
                placeholder="Первый вклад"
                maxLength={255}
              />
            </div>
            <p style={{ marginTop: 12, fontSize: 13, color: '#6b7280' }}>
              💡 Сумма будет учтена как расход в категории «Накопления» за сегодня.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setContributeGoal(null)}>
                Отмена
              </button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Сохранение…' : 'Внести вклад'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
