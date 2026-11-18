import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 6) {
      setError('Пароль должен содержать не менее 6 символов')
      return
    }
    setSending(true)
    try {
      await register(email.trim(), username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'Не удалось зарегистрироваться')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-logo">💰</div>
        <h1>BALANCE</h1>
        <p className="auth-subtitle">Регистрация нового пользователя</p>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="form-field">
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.ru"
            required
            autoFocus
          />
        </div>

        <div className="form-field">
          <label htmlFor="username">Имя пользователя</label>
          <input
            id="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Иван"
            minLength={2}
            maxLength={100}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="password">Пароль (не менее 6 символов)</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            minLength={6}
            required
          />
        </div>

        <button type="submit" className="btn btn-primary btn-block" disabled={sending}>
          {sending ? 'Создание…' : 'Создать аккаунт'}
        </button>

        <p className="auth-switch">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  )
}
