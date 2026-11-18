// Лёгкий HTTP-клиент поверх fetch: прокидывает JWT, сериализует JSON,
// разбирает ошибки бэкенда (detail).
const BASE = '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let body = options.body
  if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(body)
  }

  const resp = await fetch(BASE + path, { ...options, headers, body })

  if (resp.status === 204) return null
  const text = await resp.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!resp.ok) {
    let msg = 'Произошла ошибка при выполнении запроса'
    if (data && typeof data.detail === 'string') msg = data.detail
    else if (data && Array.isArray(data.detail)) {
      msg = data.detail.map((d) => (d.msg ? d.msg : String(d))).join('; ')
    }
    const err = new Error(msg)
    err.status = resp.status
    throw err
  }
  return data
}

const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  del: (path) => request(path, { method: 'DELETE' }),

  // OAuth2 password flow: бэкенд ожидает form-urlencoded
  login: (email, password) =>
    request('/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    }),

  register: (email, username, password) =>
    request('/auth/register', { method: 'POST', body: { email, username, password } }),

  importCsv: (path, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request(path, { method: 'POST', body: fd })
  },
}

export default api
