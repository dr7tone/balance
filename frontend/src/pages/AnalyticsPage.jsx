import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { formatMoney, todayISO, monthStartISO, currentMonth } from '../utils/format'

const PALETTE = ['#0e9f6e', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#64748b']

const MONTH_NAMES = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

export default function AnalyticsPage() {
  const today = todayISO()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [summary, setSummary] = useState(null)
  const [monthly, setMonthly] = useState([])
  const [catExpense, setCatExpense] = useState([])
  const [catIncome, setCatIncome] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)

    Promise.all([
      api.get(`/analytics/summary?${params.toString()}`),
      api.get('/analytics/monthly?months=6'),
      api.get(`/analytics/categories?type=expense&${params.toString()}`),
      api.get(`/analytics/categories?type=income&${params.toString()}`),
    ])
      .then(([s, m, ce, ci]) => {
        setSummary(s)
        setMonthly(
          m.map((p) => {
            const [y, mo] = p.month.split('-')
            return {
              ...p,
              label: `${MONTH_NAMES[Number(mo) - 1]} ${y}`,
              income: Number(p.income),
              expense: Number(p.expense),
            }
          }),
        )
        setCatExpense((ce || []).filter((x) => x.amount > 0))
        setCatIncome((ci || []).filter((x) => x.amount > 0))
      })
      .catch((err) => setError(err.message))
  }, [dateFrom, dateTo])

  useEffect(load, [load])

  const prevMonthISO = () => {
    const d = new Date()
    d.setDate(1)
    d.setMonth(d.getMonth() - 1)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  }

  const lastDayPrevISO = () => {
    const d = new Date()
    d.setDate(0)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  const presets = [
    { label: 'Весь период', from: '', to: '' },
    { label: 'Текущий месяц', from: monthStartISO(currentMonth()), to: today },
    { label: 'Прошлый месяц', from: monthStartISO(prevMonthISO()), to: lastDayPrevISO() },
  ]

  const applyPreset = (p) => {
    setDateFrom(p.from)
    setDateTo(p.to)
  }

  const pieData = (rows) =>
    rows.map((r) => ({ name: r.category_name || 'Без категории', value: r.amount }))

  return (
    <div>
      <PageHeader title="Аналитика" subtitle="Сводка, динамика и структура доходов и расходов" />

      {error && <div className="alert alert-error">{error}</div>}

      <div className="filters">
        <div className="filter-item">
          Период с
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="filter-item">
          по
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {presets.map((p) => (
          <button key={p.label} type="button" className="btn btn-secondary btn-sm" onClick={() => applyPreset(p)}>
            {p.label}
          </button>
        ))}
      </div>

      <div className="stats-grid">
        <div className="stat-card stat-income">
          <div className="stat-label">Доходы</div>
          <div className="stat-value">{summary ? formatMoney(summary.income) : '…'}</div>
          <div className="stat-hint">{summary ? `${summary.operations_count} операций за период` : ''}</div>
        </div>
        <div className="stat-card stat-expense">
          <div className="stat-label">Расходы</div>
          <div className="stat-value">{summary ? formatMoney(summary.expense) : '…'}</div>
        </div>
        <div className="stat-card stat-balance">
          <div className="stat-label">Баланс</div>
          <div className="stat-value">
            {summary ? `${summary.balance >= 0 ? '+' : '−'}${formatMoney(Math.abs(summary.balance))}` : '…'}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Динамика за последние 6 месяцев</div>
        <div className="chart-box">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthly} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${Math.round(v / 1000)}к`} />
              <Tooltip formatter={(v) => formatMoney(v)} />
              <Legend />
              <Bar dataKey="income" name="Доходы" fill="#0e9f6e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="expense" name="Расходы" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-grid" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-title">Структура расходов</div>
          {catExpense.length === 0 ? (
            <EmptyState emoji="🍩" text="Нет данных за период" />
          ) : (
            <div className="chart-box" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData(catExpense)}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={95}
                    paddingAngle={2}
                    label={(entry) => entry.name}
                    labelLine={false}
                  >
                    {pieData(catExpense).map((entry, i) => (
                      <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatMoney(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Структура доходов</div>
          {catIncome.length === 0 ? (
            <EmptyState emoji="🍩" text="Нет данных за период" />
          ) : (
            <div className="chart-box" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData(catIncome)}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={95}
                    paddingAngle={2}
                    label={(entry) => entry.name}
                    labelLine={false}
                  >
                    {pieData(catIncome).map((entry, i) => (
                      <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatMoney(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
