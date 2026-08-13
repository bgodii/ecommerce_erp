import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { useDeleteUser, useInviteUser, useResetUserPassword, useUsers } from '../hooks/queries'
import { apiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { User } from '../lib/types'

export default function Usuarios() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const { data: users, isLoading } = useUsers()
  const invite = useInviteUser()
  const resetPw = useResetUserPassword()
  const delUser = useDeleteUser()

  const [msg, setMsg] = useState('')

  // convidar
  const [inviteOpen, setInviteOpen] = useState(false)
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '' })
  const [inviteErr, setInviteErr] = useState('')
  const setNU = (k: string) => (e: any) => setNewUser((u) => ({ ...u, [k]: e.target.value }))

  // trocar senha
  const [pwTarget, setPwTarget] = useState<User | null>(null)
  const [pwValue, setPwValue] = useState('')
  const [pwErr, setPwErr] = useState('')

  function openInvite() {
    setNewUser({ name: '', email: '', password: '' })
    setInviteErr('')
    setInviteOpen(true)
  }

  async function submitInvite(e: FormEvent) {
    e.preventDefault()
    setInviteErr('')
    try {
      await invite.mutateAsync({ ...newUser, role: 'member' })
      setMsg(`Usuário ${newUser.email} adicionado.`)
      setInviteOpen(false)
    } catch (e) {
      setInviteErr(apiError(e))
    }
  }

  function openPw(u: User) {
    setPwTarget(u)
    setPwValue('')
    setPwErr('')
  }

  async function submitPw(e: FormEvent) {
    e.preventDefault()
    if (!pwTarget) return
    setPwErr('')
    try {
      await resetPw.mutateAsync({ id: pwTarget.id, password: pwValue })
      setMsg(`Senha de ${pwTarget.email} atualizada.`)
      setPwTarget(null)
    } catch (e) {
      setPwErr(apiError(e))
    }
  }

  async function remove(u: User) {
    if (!confirm(`Excluir a conta de ${u.email}? Esta ação não pode ser desfeita.`)) return
    try {
      await delUser.mutateAsync(u.id)
      setMsg(`Conta de ${u.email} excluída.`)
    } catch (e) {
      alert(apiError(e))
    }
  }

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Usuários</div>
          <div className="page-sub">Contas com acesso à sua loja</div>
        </div>
        {isOwner && (
          <button className="btn" onClick={openInvite}>
            + Adicionar usuário
          </button>
        )}
      </div>

      {msg && <div className="status-line pos" style={{ marginBottom: 10 }}>{msg}</div>}
      {!isOwner && (
        <div className="page-sub">Apenas o dono da loja pode gerenciar usuários.</div>
      )}

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Papel</th>
                {isOwner && <th></th>}
              </tr>
            </thead>
            <tbody>
              {users?.map((u) => (
                <tr key={u.id}>
                  <td>
                    {u.name}
                    {u.id === user?.id && <span className="pill" style={{ marginLeft: 8 }}>você</span>}
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`badge ${u.role === 'owner' ? 'on' : 'off'}`}>{u.role}</span>
                  </td>
                  {isOwner && (
                    <td>
                      <div className="row-actions">
                        <button className="btn ghost sm" onClick={() => openPw(u)}>
                          Trocar senha
                        </button>
                        <button
                          className="btn ghost sm neg"
                          onClick={() => remove(u)}
                          disabled={u.id === user?.id}
                          title={u.id === user?.id ? 'Você não pode excluir a própria conta' : ''}
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {inviteOpen && (
        <Modal title="Adicionar usuário" onClose={() => setInviteOpen(false)}>
          {inviteErr && <div className="error">{inviteErr}</div>}
          <form onSubmit={submitInvite}>
            <div className="field">
              <label>Nome</label>
              <input value={newUser.name} onChange={setNU('name')} required />
            </div>
            <div className="field">
              <label>E-mail</label>
              <input type="email" value={newUser.email} onChange={setNU('email')} required />
            </div>
            <div className="field">
              <label>Senha (mín. 6)</label>
              <input
                type="password"
                minLength={6}
                value={newUser.password}
                onChange={setNU('password')}
                required
              />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setInviteOpen(false)}>
                Cancelar
              </button>
              <button className="btn" disabled={invite.isPending}>
                {invite.isPending ? 'Adicionando…' : 'Adicionar'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {pwTarget && (
        <Modal title={`Trocar senha — ${pwTarget.email}`} onClose={() => setPwTarget(null)}>
          {pwErr && <div className="error">{pwErr}</div>}
          <form onSubmit={submitPw}>
            <div className="field">
              <label>Nova senha (mín. 6)</label>
              <input
                type="password"
                minLength={6}
                value={pwValue}
                onChange={(e) => setPwValue(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setPwTarget(null)}>
                Cancelar
              </button>
              <button className="btn" disabled={resetPw.isPending}>
                {resetPw.isPending ? 'Salvando…' : 'Salvar nova senha'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  )
}
