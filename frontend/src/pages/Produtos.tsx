import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import Th from '../components/Th'
import { useAdjustStock, useDeleteProduct, useProducts, useSaveProduct } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum } from '../lib/format'
import type { Product } from '../lib/types'

const empty = { sku: '', nome: '', variacao: '', dropdown_name: '', ativo: true }

export default function Produtos() {
  const { data: products, isLoading } = useProducts()
  const save = useSaveProduct()
  const del = useDeleteProduct()
  const adjust = useAdjustStock()
  // acerto de estoque (cria entrada com a diferença, no custo informado)
  const [ajuste, setAjuste] = useState<Product | null>(null)
  const [ajusteForm, setAjusteForm] = useState({ estoque: '', custo: '' })
  const [ajusteMsg, setAjusteMsg] = useState('')
  const [ajusteErr, setAjusteErr] = useState('')

  function abrirAjuste(p: Product) {
    setAjuste(p)
    setAjusteForm({
      estoque: String(Math.max(p.saldo_real, 0)),
      custo: p.custo_medio_atual > 0 ? String(p.custo_medio_atual) : '',
    })
    setAjusteErr('')
    setAjusteMsg('')
  }

  async function submitAjuste(e: FormEvent) {
    e.preventDefault()
    if (!ajuste) return
    setAjusteErr('')
    try {
      const r = await adjust.mutateAsync({
        id: ajuste.id,
        estoque_atual: Number(ajusteForm.estoque),
        custo_unitario: Number(ajusteForm.custo),
      })
      setAjusteMsg(r.mensagem)
      setAjuste(null)
    } catch (e) {
      setAjusteErr(apiError(e))
    }
  }
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
          {ajusteMsg && <div className="status-line pos">{ajusteMsg}</div>}
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
                <Th label="SKU" help="Código único do produto no seu catálogo" />
                <Th label="Nome (dropdown)" help="Nome exibido ao lançar vendas" />
                <Th label="Variação" help="Cor, tamanho ou modelo" />
                <Th label="Ativo" help="Produtos inativos não aparecem para venda" />
                <Th label="Entradas" help="Total de unidades que você comprou (soma dos lotes)" num />
                <Th label="Vend. diretas" help="Unidades vendidas avulsas (fora de kits)" num />
                <Th label="Em kits" help="Unidades consumidas dentro de kits vendidos" num />
                <Th label="Estoque" help="Entradas − vendas diretas − consumo em kits" num />
                <Th label="Valor estoque" help="Quanto o estoque atual vale ao custo de compra" num />
                <Th label="Custo médio" help="Custo médio das unidades ainda em estoque" num />
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
                    {p.deficit > 0 ? (
                      <span
                        className="verdict atencao"
                        title={`Vendeu ${p.deficit} un a mais do que as entradas registradas. Clique em "Ajustar estoque" e informe quanto você tem.`}
                      >
                        faltam {fmtNum(p.deficit)}
                      </span>
                    ) : (
                      fmtNum(p.estoque_atual)
                    )}
                  </td>
                  <td className="num">{fmtBRL(p.valor_estoque)}</td>
                  <td className="num">{fmtBRL(p.custo_medio_atual)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost sm" onClick={() => abrirAjuste(p)}>
                        Ajustar estoque
                      </button>
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

      {ajuste && (
        <Modal title={`Ajustar estoque — ${ajuste.dropdown_name}`} onClose={() => setAjuste(null)}>
          {ajusteErr && <div className="error">{ajusteErr}</div>}
          <table style={{ marginBottom: 12 }}>
            <tbody>
              <tr>
                <td className="muted">Compras registradas</td>
                <td className="num">{fmtNum(ajuste.entradas)}</td>
              </tr>
              <tr>
                <td className="muted">Saídas (vendas + kits)</td>
                <td className="num">−{fmtNum(ajuste.vendas_diretas + ajuste.consumo_kits)}</td>
              </tr>
              <tr>
                <td className="muted">Saldo calculado</td>
                <td className={`num ${ajuste.saldo_real < 0 ? 'neg' : ''}`} style={{ fontWeight: 700 }}>
                  {fmtNum(ajuste.saldo_real)}
                </td>
              </tr>
            </tbody>
          </table>
          <form onSubmit={submitAjuste}>
            <div className="form-grid">
              <div className="field">
                <label>Quantas unidades você tem hoje?</label>
                <input
                  type="number"
                  min={0}
                  value={ajusteForm.estoque}
                  onChange={(e) => setAjusteForm((f) => ({ ...f, estoque: e.target.value }))}
                  required
                  autoFocus
                />
              </div>
              <div className="field">
                <label>Quanto pagou por unidade (R$)?</label>
                <input
                  type="number"
                  step="0.01"
                  min={0.01}
                  value={ajusteForm.custo}
                  onChange={(e) => setAjusteForm((f) => ({ ...f, custo: e.target.value }))}
                  required
                />
              </div>
            </div>
            <p className="status-line">
              Vou criar uma <b>entrada de acerto</b> com a diferença, datada antes da sua primeira
              venda — assim o FIFO das vendas antigas encontra estoque e o lucro passa a considerar o
              custo real. Nenhum lote existente é alterado.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setAjuste(null)}>
                Cancelar
              </button>
              <button className="btn" disabled={adjust.isPending}>
                {adjust.isPending ? 'Ajustando…' : 'Ajustar estoque'}
              </button>
            </div>
          </form>
        </Modal>
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
