import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { useChannels, useDeleteChannel, useSaveChannel } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtPct } from '../lib/format'
import type { Channel } from '../lib/types'

const empty = { name: '', taxa_pct: '20', taxa_fixa: '4', taxa_afiliado_pct: '0', ativo: true }

export default function Ecommerces() {
  const { data: channels, isLoading } = useChannels()
  const save = useSaveChannel()
  const del = useDeleteChannel()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Channel | null>(null)
  const [form, setForm] = useState<any>(empty)
  const [err, setErr] = useState('')

  const set = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  function openNew() {
    setEditing(null)
    setForm(empty)
    setErr('')
    setOpen(true)
  }
  function openEdit(c: Channel) {
    setEditing(c)
    setForm({
      name: c.name,
      taxa_pct: String(+(c.taxa_pct * 100).toFixed(4)),
      taxa_fixa: String(c.taxa_fixa),
      taxa_afiliado_pct: String(+(c.taxa_afiliado_pct * 100).toFixed(4)),
      ativo: c.ativo,
    })
    setErr('')
    setOpen(true)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await save.mutateAsync({
        id: editing?.id,
        name: form.name,
        taxa_pct: Number(form.taxa_pct) / 100,
        taxa_fixa: Number(form.taxa_fixa),
        taxa_afiliado_pct: Number(form.taxa_afiliado_pct) / 100,
        ativo: form.ativo,
      })
      setOpen(false)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function remove(c: Channel) {
    if (!confirm(`Excluir o e-commerce "${c.name}"? As vendas ficam sem canal.`)) return
    try {
      await del.mutateAsync(c.id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">E-commerces</div>
          <div className="page-sub">Cadastre cada marketplace com suas taxas próprias</div>
        </div>
        <button className="btn" onClick={openNew}>
          + Novo e-commerce
        </button>
      </div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th className="num">Taxa (%)</th>
                <th className="num">Taxa fixa</th>
                <th className="num">Afiliado (%)</th>
                <th>Ativo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {channels?.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td className="num">{fmtPct(c.taxa_pct)}</td>
                  <td className="num">{fmtBRL(c.taxa_fixa)}</td>
                  <td className="num">{fmtPct(c.taxa_afiliado_pct)}</td>
                  <td>
                    <span className={`badge ${c.ativo ? 'on' : 'off'}`}>{c.ativo ? 'Sim' : 'Não'}</span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost sm" onClick={() => openEdit(c)}>
                        Editar
                      </button>
                      <button className="btn ghost sm neg" onClick={() => remove(c)}>
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!channels?.length && (
                <tr>
                  <td colSpan={6} className="center-msg">
                    Nenhum e-commerce cadastrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <Modal title={editing ? 'Editar e-commerce' : 'Novo e-commerce'} onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="field">
              <label>Nome (ex.: Shopee, TikTok, Mercado Livre, Shein)</label>
              <input value={form.name} onChange={set('name')} required />
            </div>
            <div className="form-grid">
              <div className="field">
                <label>Taxa do marketplace (%)</label>
                <input type="number" step="0.01" value={form.taxa_pct} onChange={set('taxa_pct')} />
              </div>
              <div className="field">
                <label>Taxa fixa por pedido (R$)</label>
                <input type="number" step="0.01" value={form.taxa_fixa} onChange={set('taxa_fixa')} />
              </div>
              <div className="field">
                <label>Taxa afiliado padrão (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.taxa_afiliado_pct}
                  onChange={set('taxa_afiliado_pct')}
                />
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={form.ativo}
                    onChange={set('ativo')}
                    style={{ width: 'auto', marginRight: 8 }}
                  />
                  Ativo
                </label>
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setOpen(false)}>
                Cancelar
              </button>
              <button className="btn" disabled={save.isPending}>
                {save.isPending ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  )
}
