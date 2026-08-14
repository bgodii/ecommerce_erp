import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { SortTh, useSort } from '../components/Sortable'
import Th from '../components/Th'
import { useDeleteLot, useLots, useProducts, useSaveLot } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtDate, fmtNum, todayISO } from '../lib/format'
import type { StockLot } from '../lib/types'

export default function Entradas() {
  const { data: lots, isLoading } = useLots()
  const sort = useSort<StockLot>(lots, 'data_entrada', 'desc')
  const { data: products } = useProducts()
  const save = useSaveLot()
  const del = useDeleteLot()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<StockLot | null>(null)
  const [err, setErr] = useState('')
  const [form, setForm] = useState<any>({
    product_id: '',
    data_entrada: todayISO(),
    qty_in: 1,
    unit_cost: 0,
    lote_code: '',
  })

  const set = (k: string) => (e: any) => setForm((f: any) => ({ ...f, [k]: e.target.value }))

  function openNew() {
    setEditing(null)
    setErr('')
    setForm({ product_id: '', data_entrada: todayISO(), qty_in: 1, unit_cost: 0, lote_code: '' })
    setOpen(true)
  }

  function openEdit(l: StockLot) {
    setEditing(l)
    setErr('')
    setForm({
      product_id: String(l.product_id),
      data_entrada: (l.data_entrada || '').slice(0, 10),
      qty_in: l.qty_in,
      unit_cost: l.unit_cost,
      lote_code: l.lote_code ?? '',
    })
    setOpen(true)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await save.mutateAsync({
        id: editing?.id,
        product_id: Number(form.product_id),
        data_entrada: form.data_entrada,
        qty_in: Number(form.qty_in),
        unit_cost: Number(form.unit_cost),
        lote_code: form.lote_code || null,
      })
      setOpen(false)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function remove(id: number) {
    if (!confirm('Excluir este lote?')) return
    try {
      await del.mutateAsync(id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Entradas de estoque</div>
          <div className="page-sub">Cada compra é um lote. Se o custo mudar, crie um novo lote (FIFO).</div>
        </div>
        <button className="btn" onClick={openNew} disabled={!products?.length}>
          + Nova entrada
        </button>
      </div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <Th label="Lote" help="Identificação da compra (cada compra é um lote)" />
                <SortTh<StockLot> label="Data" k="data_entrada" sort={sort} help="Data da compra — define a ordem do FIFO" />
                <Th label="Produto" help="Produto que entrou no estoque" />
                <Th label="Qtd" help="Unidades compradas neste lote" num />
                <Th label="Custo unit." help="Quanto você pagou por unidade" num />
                <Th label="Custo total" help="Qtd × custo unitário" num />
                <Th label="Saldo" help="Unidades deste lote que ainda não foram vendidas" num />
                <Th label="Valor saldo" help="Quanto ainda resta em valor neste lote" num />
                <Th label="Status" help="Disponível = intacto · Parcial = em consumo · Esgotado = todo vendido" />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((l) => (
                <tr key={l.id}>
                  <td>{l.lote_code || `#${l.id}`}</td>
                  <td>{fmtDate(l.data_entrada)}</td>
                  <td>{l.produto}</td>
                  <td className="num">{fmtNum(l.qty_in)}</td>
                  <td className="num">{fmtBRL(l.unit_cost)}</td>
                  <td className="num">{fmtBRL(l.custo_total)}</td>
                  <td className="num">{fmtNum(l.remaining)}</td>
                  <td className="num">{fmtBRL(l.valor_saldo)}</td>
                  <td>
                    <span className="pill">{l.status}</span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost sm" onClick={() => openEdit(l)}>
                        Editar
                      </button>
                      <button className="btn ghost sm neg" onClick={() => remove(l.id)}>
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!sort.sorted.length && (
                <tr>
                  <td colSpan={10} className="center-msg">
                    Nenhuma entrada. Cadastre um produto e registre a primeira compra.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <Modal title={editing ? 'Editar entrada' : 'Nova entrada'} onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="field">
              <label>Produto</label>
              <select value={form.product_id} onChange={set('product_id')} required disabled={!!editing}>
                <option value="">Selecione…</option>
                {products?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.dropdown_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-grid">
              <div className="field">
                <label>Data de entrada</label>
                <input type="date" value={form.data_entrada} onChange={set('data_entrada')} required />
              </div>
              <div className="field">
                <label>Código do lote (opcional)</label>
                <input value={form.lote_code} onChange={set('lote_code')} placeholder="L0001" />
              </div>
              <div className="field">
                <label>Quantidade</label>
                <input type="number" min={1} value={form.qty_in} onChange={set('qty_in')} required />
              </div>
              <div className="field">
                <label>Custo unitário (R$)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.unit_cost}
                  onChange={set('unit_cost')}
                  required
                />
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
