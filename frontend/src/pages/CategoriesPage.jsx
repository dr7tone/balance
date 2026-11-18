import { useCallback, useEffect, useState } from 'react'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'

export default function CategoriesPage() {
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('expense')
  const [editId, setEditId] = useState(null)
  const [editName, setEditName] = useState('')

  const load = useCallback(() => {
    api.get('/categories').then(setCategories).catch(() => setCategories([]))
  }, [])

  useEffect(load, [load])

  const income = categories.filter((c) => c.type === 'income')
  const expense = categories.filter((c) => c.type === 'expense')

  const add = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/categories', { name: newName.trim(), type: newType })
      setNotice('Категория добавлена')
      setNewName('')
      setAddOpen(false)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const saveEdit = async (id) => {
    setError('')
    try {
      await api.put(`/categories/${id}`, { name: editName.trim() })
      setNotice('Категория переименована')
      setEditId(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const remove = async (cat) => {
    if (cat.is_system) return
    if (!window.confirm(`Удалить категорию «${cat.name}»? Операции останутся без категории.`)) return
    try {
      await api.del(`/categories/${cat.id}`)
      setNotice('Категория удалена')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const renderGroup = (title, list) => (
    <div className="cat-group">
      <h2 style={{ marginBottom: 10 }}>{title}</h2>
      {list.length === 0 ? (
        <EmptyState text="Нет категорий" />
      ) : (
        <div className="cat-items">
          {list.map((cat) => (
            <div key={cat.id} className="cat-chip">
              {editId === cat.id ? (
                <>
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => e.key === 'Enter' && saveEdit(cat.id)}
                  />
                  <button type="button" className="btn btn-primary btn-sm" onClick={() => saveEdit(cat.id)}>
                    OK
                  </button>
                </>
              ) : (
                <>
                  <span className="cat-name">
                    {cat.name}
                    {cat.is_system && <span className="badge badge-system" style={{ marginLeft: 6 }}>системная</span>}
                  </span>
                  <span className="cat-actions">
                    <button
                      type="button"
                      className="icon-btn"
                      title="Переименовать"
                      onClick={() => {
                        setEditId(cat.id)
                        setEditName(cat.name)
                      }}
                    >
                      ✏️
                    </button>
                    {!cat.is_system && (
                      <button
                        type="button"
                        className="icon-btn danger"
                        title="Удалить"
                        onClick={() => remove(cat)}
                      >
                        🗑️
                      </button>
                    )}
                  </span>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const form = (
    <form className="card" onSubmit={add} style={{ marginBottom: 20 }}>
      <div className="card-title">Новая категория</div>
      <div className="form-row">
        <div className="form-field">
          <label htmlFor="cat-name">Название</label>
          <input
            id="cat-name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Например: Кофе"
            maxLength={100}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="cat-type">Тип</label>
          <select id="cat-type" value={newType} onChange={(e) => setNewType(e.target.value)}>
            <option value="expense">Расход</option>
            <option value="income">Доход</option>
          </select>
        </div>
      </div>
      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={() => setAddOpen(false)}>
          Отмена
        </button>
        <button type="submit" className="btn btn-primary">
          Добавить
        </button>
      </div>
    </form>
  )

  return (
    <div>
      <PageHeader
        title="Категории"
        subtitle="Стандартный набор создаётся автоматически при регистрации"
        action={
          <button type="button" className="btn btn-primary" onClick={() => setAddOpen((v) => !v)}>
            {addOpen ? 'Скрыть форму' : '+ Добавить категорию'}
          </button>
        }
      />

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {addOpen && form}

      {renderGroup('Расходы', expense)}
      {renderGroup('Доходы', income)}
    </div>
  )
}
