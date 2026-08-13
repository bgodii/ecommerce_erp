import { FormEvent, useEffect, useState } from 'react'
import { useSettings, useUpdateSettings } from '../hooks/queries'
import { apiError } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Configuracoes() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const { data: settings } = useSettings()
  const updateSettings = useUpdateSettings()

  const [form, setForm] = useState({ shopee: '', fixa: '', afiliado: '' })
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  useEffect(() => {
    if (settings) {
      setForm({
        shopee: String(+(settings.taxa_shopee_pct * 100).toFixed(4)),
        fixa: String(settings.taxa_fixa),
        afiliado: String(+(settings.taxa_afiliado_pct * 100).toFixed(4)),
      })
    }
  }, [settings])

  async function saveSettings(e: FormEvent) {
    e.preventDefault()
    setMsg('')
    setErr('')
    try {
      await updateSettings.mutateAsync({
        taxa_shopee_pct: Number(form.shopee) / 100,
        taxa_fixa: Number(form.fixa),
        taxa_afiliado_pct: Number(form.afiliado) / 100,
      })
      setMsg('Configurações salvas.')
    } catch (e) {
      setErr(apiError(e))
    }
  }

  return (
    <>
      <div className="page-title">Configurações</div>
      <div className="page-sub">Taxas da loja usadas no cálculo de vendas e precificação</div>

      <div className="card" style={{ maxWidth: 460 }}>
        <h3>Taxas da Shopee</h3>
        {msg && <div className="status-line pos">{msg}</div>}
        {err && <div className="error">{err}</div>}
        <form onSubmit={saveSettings}>
          <div className="field">
            <label>Taxa Shopee (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.shopee}
              onChange={(e) => setForm((f) => ({ ...f, shopee: e.target.value }))}
              disabled={!isOwner}
            />
          </div>
          <div className="field">
            <label>Taxa fixa por pedido (R$)</label>
            <input
              type="number"
              step="0.01"
              value={form.fixa}
              onChange={(e) => setForm((f) => ({ ...f, fixa: e.target.value }))}
              disabled={!isOwner}
            />
          </div>
          <div className="field">
            <label>Taxa afiliado padrão (%)</label>
            <input
              type="number"
              step="0.01"
              value={form.afiliado}
              onChange={(e) => setForm((f) => ({ ...f, afiliado: e.target.value }))}
              disabled={!isOwner}
            />
          </div>
          {isOwner ? (
            <button className="btn" disabled={updateSettings.isPending}>
              {updateSettings.isPending ? 'Salvando…' : 'Salvar taxas'}
            </button>
          ) : (
            <p className="muted">Apenas o dono da loja pode alterar as taxas.</p>
          )}
        </form>
      </div>
    </>
  )
}
