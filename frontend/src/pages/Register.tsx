import { FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiError } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Register() {
  const { user, register } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', org_name: '' })
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/" replace />

  const set = (k: string) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await register({
        name: form.name,
        email: form.email,
        password: form.password,
        org_name: form.org_name || undefined,
      })
      nav('/')
    } catch (e) {
      setErr(apiError(e, 'Não foi possível criar a conta'))
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
          Crie sua loja em segundos
        </p>
        {err && <div className="error">{err}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Seu nome</label>
            <input value={form.name} onChange={set('name')} required />
          </div>
          <div className="field">
            <label>Nome da loja</label>
            <input value={form.org_name} onChange={set('org_name')} placeholder="Minha Loja" />
          </div>
          <div className="field">
            <label>E-mail</label>
            <input type="email" value={form.email} onChange={set('email')} required />
          </div>
          <div className="field">
            <label>Senha (mín. 6 caracteres)</label>
            <input
              type="password"
              value={form.password}
              onChange={set('password')}
              minLength={6}
              required
            />
          </div>
          <button className="btn" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Criando…' : 'Criar loja'}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Já tem conta?{' '}
          <Link className="link" to="/login">
            Entrar
          </Link>
        </p>
      </div>
    </div>
  )
}
