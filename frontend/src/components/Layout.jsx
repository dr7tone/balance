import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/', label: 'Дашборд', emoji: '📊', end: true },
  { to: '/operations', label: 'Операции', emoji: '💳' },
  { to: '/categories', label: 'Категории', emoji: '🏷️' },
  { to: '/budgets', label: 'Бюджет', emoji: '🎯' },
  { to: '/goals', label: 'Мечты', emoji: '💎' },
  { to: '/analytics', label: 'Аналитика', emoji: '📈' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">💰 BALANCE</div>

        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              <span className="nav-emoji">{item.emoji}</span>
              {item.label}
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink
              to="/admin"
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              <span className="nav-emoji">⚙️</span>
              Администрирование
            </NavLink>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-avatar">{(user?.username || '?')[0].toUpperCase()}</div>
            <div className="user-info">
              <div className="user-name">{user?.username}</div>
              <div className="user-email">{user?.email}</div>
            </div>
          </div>
          <button type="button" className="btn btn-ghost btn-block" onClick={onLogout}>
            🚪 Выйти
          </button>
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
