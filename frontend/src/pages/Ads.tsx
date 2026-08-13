import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { SortTh, useSort } from '../components/Sortable'
import { useAds, useDeleteAd, useSaveAd } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtDate, todayISO } from '../lib/format'
import type { AdSpend } from '../lib/types'

export default function Ads() {
  const { data: ads, isLoading } = useAds()
  const sort = useSort<AdSpend>(ads, 'data', 'desc')
  const save = useSaveAd()
  const del = useDeleteAd()
  const [open, setOpen] = useState(false)
  const [err, setErr] = useState('')
  const [form, setForm] = useState<any>({ data: todayISO(), canal: 'Shopee Ads', valor: 0, observacao: '' })
  const set = (k: string) => (e: any) => setForm((f: any) => ({ ...f, [k]: e.target.value }))

  function openNew() {
    setErr('')
    setForm({ data: todayISO(), canal: 'Shopee Ads', valor: 0, observacao: '' })
    setOpen(true)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await save.mutateAsync({
        data: form.data,
        canal: form.canal || null,
        valor: Number(form.valor),
        observacao: form.observacao || null,
      })
      setOpen(false)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function remove(id: number) {
    if (!confirm('Excluir este lançamento?')) return
    try {
      await del.mutateAsync(id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  const total = ads?.reduce((s, a) => s + a.valor, 0) ?? 0

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Ads</div>
          <div className="page-sub">Registre o investimento em anúncios por data e campanha</div>
        </div>
        <button className="btn" onClick={openNew}>
          + Novo lançamento
        </button>
      </div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh<AdSpend> label="Data" k="data" sort={sort} />
                <th>Canal / Campanha</th>
                <th className="num">Valor</th>
                <th>Observação</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((a) => (
                <tr key={a.id}>
                  <td>{fmtDate(a.data)}</td>
                  <td>{a.canal}</td>
                  <td className="num">{fmtBRL(a.valor)}</td>
                  <td>{a.observacao}</td>
                  <td>
                    <button className="btn ghost sm neg" onClick={() => remove(a.id)}>
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
              {!sort.sorted.length && (
                <tr>
                  <td colSpan={5} className="center-msg">
                    Nenhum lançamento de Ads.
                  </td>
                </tr>
              )}
            </tbody>
            {!!ads?.length && (
              <tfoot>
                <tr>
                  <td colSpan={2} style={{ fontWeight: 700 }}>
                    Total
                  </td>
                  <td className="num" style={{ fontWeight: 700 }}>
                    {fmtBRL(total)}
                  </td>
                  <td colSpan={2}></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}

      {open && (
        <Modal title="Novo lançamento de Ads" onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label>Data</label>
                <input type="date" value={form.data} onChange={set('data')} required />
              </div>
              <div className="field">
                <label>Canal / Campanha</label>
                <input value={form.canal} onChange={set('canal')} />
              </div>
              <div className="field">
                <label>Valor (R$)</label>
                <input type="number" min={0} step="0.01" value={form.valor} onChange={set('valor')} required />
              </div>
              <div className="field">
                <label>Observação</label>
                <input value={form.observacao} onChange={set('observacao')} />
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
