import { FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiError } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await login(email, password)
      nav('/')
    } catch (e) {
      setErr(apiError(e, 'E-mail ou senha inválidos'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth">
      <div className="auth-card">
        <div className="logo">
          ERP <span>Shopee</span>
        </div>
        <p className="muted" style={{ marginBottom: 20 }}>
          Entre para gerenciar sua loja
        </p>
        {err && <div className="error">{err}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>E-mail</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Não tem conta?{' '}
          <Link className="link" to="/register">
            Criar minha loja
          </Link>
        </p>
      </div>
    </div>
  )
}
