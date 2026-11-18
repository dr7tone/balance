import { useCallback, useEffect, useRef, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import Modal from '../components/Modal'
import EmptyState from '../components/EmptyState'
import { formatMoney, formatDate, todayISO } from '../utils/format'

const EMPTY_FORM = { type: 'expense', amount: '', date: todayISO(), category_id: '', comment: '' }

export default function OperationsPage() {
  const [categories, setCategories] = useState([])
  const [ops, setOps] = useState({ total: 0, items: [] })
  const [filters, setFilters] = useState({
    type: '',
    category_id: '',
    date_from: '',
    date_to: '',
    search: '',
  })
  const [editing, setEditing] = useState(null) // null | 'new' | operation
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const fileRef = useRef(null)

  const loadCategories = useCallback(() => {
    api.get('/categories').then(setCategories).catch(() => setCategories([]))
  }, [])

  const loadOps = useCallback(() => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params.set(k, v)
    })
    api.get(`/operations?${params.toString()}`).then(setOps).catch(() => {})
  }, [filters])

  useEffect(() => {
    loadCategories()
    loadOps()
  }, [loadCategories, loadOps])

  const setFilter = (key, value) => setFilters((f) => ({ ...f, [key]: value }))

  const openNew = () => {
    setForm(EMPTY_FORM)
    setEditing('new')
  }

  const openEdit = (op) => {
    setForm({
      type: op.type,
      amount: String(op.amount),
      date: op.date,
      category_id: op.category_id != null ? String(op.category_id) : '',
      comment: op.comment || '',
    })
    setEditing(op)
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    const payload = {
      type: form.type,
      amount: Number(form.amount),
      date: form.date,
      category_id: form.category_id ? Number(form.category_id) : null,
      comment: form.comment,
    }
    try {
      if (editing === 'new') {
        await api.post('/operations', payload)
        setNotice('Операция добавлена')
      } else {
        await api.put(`/operations/${editing.id}`, payload)
        setNotice('Операция обновлена')
      }
      setEditing(null)
      loadOps()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (op) => {
    if (!window.confirm(`Удалить операцию ${formatMoney(op.amount)} от ${formatDate(op.date)}?`)) return
    try {
      await api.del(`/operations/${op.id}`)
      setNotice('Операция удалена')
      loadOps()
    } catch (err) {
      setError(err.message)
    }
  }

  const exportCsv = async () => {
    const params = new URLSearchParams()
    if (filters.date_from) params.set('date_from', filters.date_from)
    if (filters.date_to) params.set('date_to', filters.date_to)
    const token = localStorage.getItem('token')
    try {
      const resp = await fetch(`/api/operations/export?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!resp.ok) throw new Error('Не удалось выгрузить CSV')
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'balance_operations.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }

  const importCsv = async (file) => {
    setError('')
    setBusy(true)
    try {
      const res = await api.importCsv('/operations/import', file)
      setNotice(`Импортировано: ${res.imported}, пропущено: ${res.skipped}`)
      loadOps()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const typeCategories = categories.filter((c) => c.type === form.type)

  return (
    <div>
      <PageHeader
        title="Операции"
        subtitle="Доходы и расходы: добавление, редактирование, поиск и фильтрация"
        action={
          <>
            <button type="button" className="btn btn-secondary btn-sm" onClick={exportCsv}>
              ⬇️ Экспорт CSV
            </button>{' '}
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()}>
              ⬆️ Импорт CSV
            </button>{' '}
            <button type="button" className="btn btn-primary btn-sm" onClick={openNew}>
              + Новая операция
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: 'none' }}
              onChange={(e) => e.target.files[0] && importCsv(e.target.files[0])}
            />
          </>
        }
      />

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      <div className="filters">
        <div className="filter-item">
          Тип
          <select value={filters.type} onChange={(e) => setFilter('type', e.target.value)}>
            <option value="">Все</option>
            <option value="income">Доход</option>
            <option value="expense">Расход</option>
          </select>
        </div>
        <div className="filter-item">
          Категория
          <select value={filters.category_id} onChange={(e) => setFilter('category_id', e.target.value)}>
            <option value="">Все</option>
            {categories.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name} ({c.type === 'income' ? 'доход' : 'расход'})
              </option>
            ))}
          </select>
        </div>
        <div className="filter-item">
          С даты
          <input type="date" value={filters.date_from} onChange={(e) => setFilter('date_from', e.target.value)} />
        </div>
        <div className="filter-item">
          По дату
          <input type="date" value={filters.date_to} onChange={(e) => setFilter('date_to', e.target.value)} />
        </div>
        <div className="filter-item">
          Поиск по комментарию
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilter('search', e.target.value)}
            placeholder="Например: зарплата"
          />
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => setFilters({ type: '', category_id: '', date_from: '', date_to: '', search: '' })}
        >
          Сбросить
        </button>
      </div>

      <div className="card">
        <div style={{ marginBottom: 10, color: '#6b7280', fontSize: 13 }}>
          Найдено операций: <strong>{ops.total}</strong>
        </div>
        {ops.items.length === 0 ? (
          <EmptyState emoji="🗒️" text="Ни одной операции не найдено" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Категория</th>
                  <th>Комментарий</th>
                  <th>Сумма</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ops.items.map((op) => (
                  <tr key={op.id}>
                    <td>{formatDate(op.date)}</td>
                    <td>
                      <span className={`badge ${op.type === 'income' ? 'badge-income' : 'badge-expense'}`}>
                        {op.type === 'income' ? 'Доход' : 'Расход'}
                      </span>
                    </td>
                    <td>{op.category_name || 'Без категории'}</td>
                    <td>{op.comment || '—'}</td>
                    <td className={op.type === 'income' ? 'amount-income' : 'amount-expense'}>
                      {op.type === 'income' ? '+' : '−'}
                      {formatMoney(op.amount)}
                    </td>
                    <td className="actions">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => openEdit(op)}>
                        ✏️
                      </button>
                      <button type="button" className="btn btn-danger btn-sm" onClick={() => remove(op)}>
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== null && (
        <Modal title={editing === 'new' ? 'Новая операция' : 'Редактирование операции'} onClose={() => setEditing(null)}>
          <form onSubmit={submit}>
            <div className="segmented">
              <button
                type="button"
                className={`segment-btn ${form.type === 'income' ? 'active-income' : ''}`}
                onClick={() => setForm((f) => ({ ...f, type: 'income' }))}
              >
                Доход
              </button>
              <button
                type="button"
                className={`segment-btn ${form.type === 'expense' ? 'active-expense' : ''}`}
                onClick={() => setForm((f) => ({ ...f, type: 'expense' }))}
              >
                Расход
              </button>
            </div>

            <div className="form-row" style={{ marginTop: 14 }}>
              <div className="form-field">
                <label htmlFor="op-amount">Сумма, ₽</label>
                <input
                  id="op-amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  placeholder="1000.00"
                  required
                />
              </div>
              <div className="form-field">
                <label htmlFor="op-date">Дата</label>
                <input
                  id="op-date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                  required
                />
              </div>
            </div>

            <div className="form-field" style={{ marginTop: 14 }}>
              <label htmlFor="op-cat">Категория</label>
              <select
                id="op-cat"
                value={form.category_id}
                onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
              >
                <option value="">Без категории</option>
                {typeCategories.map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field" style={{ marginTop: 14 }}>
              <label htmlFor="op-comment">Комментарий</label>
              <textarea
                id="op-comment"
                value={form.comment}
                onChange={(e) => setForm((f) => ({ ...f, comment: e.target.value }))}
                maxLength={500}
                placeholder="Необязательно"
              />
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setEditing(null)}>
                Отмена
              </button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Сохранение…' : 'Сохранить'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
