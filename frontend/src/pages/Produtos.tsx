import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { useDeleteProduct, useProducts, useSaveProduct } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum } from '../lib/format'
import type { Product } from '../lib/types'

const empty = { sku: '', nome: '', variacao: '', dropdown_name: '', ativo: true }

export default function Produtos() {
  const { data: products, isLoading } = useProducts()
  const save = useSaveProduct()
  const del = useDeleteProduct()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Product | null>(null)
  const [form, setForm] = useState<any>(empty)
  const [err, setErr] = useState('')

  function openNew() {
    setEditing(null)
    setForm(empty)
    setErr('')
    setOpen(true)
  }
  function openEdit(p: Product) {
    setEditing(p)
    setForm({
      sku: p.sku,
      nome: p.nome,
      variacao: p.variacao ?? '',
      dropdown_name: p.dropdown_name,
      ativo: p.ativo,
    })
    setErr('')
    setOpen(true)
  }
  const set = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await save.mutateAsync({ id: editing?.id, ...form, variacao: form.variacao || null })
      setOpen(false)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function remove(p: Product) {
    if (!confirm(`Excluir "${p.nome}"?`)) return
    try {
      await del.mutateAsync(p.id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Produtos</div>
          <div className="page-sub">Estoque = Entradas − Vendas diretas − Consumo em kits</div>
        </div>
        <button className="btn" onClick={openNew}>
          + Novo produto
        </button>
      </div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Nome (dropdown)</th>
                <th>Variação</th>
                <th>Ativo</th>
                <th className="num">Entradas</th>
                <th className="num">Vend. diretas</th>
                <th className="num">Em kits</th>
                <th className="num">Estoque</th>
                <th className="num">Valor estoque</th>
                <th className="num">Custo médio</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {products?.map((p) => (
                <tr key={p.id}>
                  <td>{p.sku}</td>
                  <td>{p.dropdown_name}</td>
                  <td>{p.variacao}</td>
                  <td>
                    <span className={`badge ${p.ativo ? 'on' : 'off'}`}>
                      {p.ativo ? 'Sim' : 'Não'}
                    </span>
                  </td>
                  <td className="num">{fmtNum(p.entradas)}</td>
                  <td className="num">{p.vendas_diretas ? `−${fmtNum(p.vendas_diretas)}` : '0'}</td>
                  <td className="num">{p.consumo_kits ? `−${fmtNum(p.consumo_kits)}` : '0'}</td>
                  <td className="num" style={{ fontWeight: 700 }}>
                    {fmtNum(p.estoque_atual)}
                  </td>
                  <td className="num">{fmtBRL(p.valor_estoque)}</td>
                  <td className="num">{fmtBRL(p.custo_medio_atual)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost sm" onClick={() => openEdit(p)}>
                        Editar
                      </button>
                      <button className="btn ghost sm neg" onClick={() => remove(p)}>
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!products?.length && (
                <tr>
                  <td colSpan={11} className="center-msg">
                    Nenhum produto ainda. Clique em “Novo produto”.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <Modal title={editing ? 'Editar produto' : 'Novo produto'} onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label>SKU</label>
                <input value={form.sku} onChange={set('sku')} required />
              </div>
              <div className="field">
                <label>Nome</label>
                <input value={form.nome} onChange={set('nome')} required />
              </div>
              <div className="field">
                <label>Variação / Cor</label>
                <input value={form.variacao} onChange={set('variacao')} />
              </div>
              <div className="field">
                <label>Nome para dropdown</label>
                <input
                  value={form.dropdown_name}
                  onChange={set('dropdown_name')}
                  placeholder="(usa o nome se vazio)"
                />
              </div>
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
