import { useCallback, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import api from '../api/client'
import PageHeader from '../components/PageHeader'
import EmptyState from '../components/EmptyState'
import { useAuth } from '../auth/AuthContext'
import { formatDate } from '../utils/format'

export default function AdminPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(() => {
    api.get('/admin/users').then(setUsers).catch(() => setUsers([]))
  }, [])

  useEffect(load, [load])

  if (user && !user.is_admin) {
    return <Navigate to="/" replace />
  }

  const toggleRole = async (target) => {
    setBusyId(target.id)
    setError('')
    try {
      await api.patch(`/admin/users/${target.id}`, { is_admin: !target.is_admin })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageHeader title="Администрирование" subtitle="Управление учётными записями пользователей" />

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-title">Пользователи ({users.length})</div>
        {users.length === 0 ? (
          <EmptyState text="Нет пользователей" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Имя</th>
                  <th>E-mail</th>
                  <th>Роль</th>
                  <th>Дата регистрации</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.username}</td>
                    <td>{u.email}</td>
                    <td>
                      <span className={`role-chip ${u.is_admin ? 'is-admin' : 'is-user'}`}>
                        {u.is_admin ? 'Администратор' : 'Пользователь'}
                      </span>
                    </td>
                    <td>{formatDate(u.created_at ? String(u.created_at).slice(0, 10) : '')}</td>
                    <td className="actions">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={u.id === user?.id || busyId === u.id}
                        onClick={() => toggleRole(u)}
                        title={
                          u.id === user?.id
                            ? 'Нельзя изменить собственную роль'
                            : u.is_admin
                              ? 'Снять права администратора'
                              : 'Назначить администратором'
                        }
                      >
                        {busyId === u.id ? '…' : u.is_admin ? 'Снять админа' : 'Сделать админом'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
