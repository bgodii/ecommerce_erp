import { FormEvent, useState } from 'react'
import Modal from '../components/Modal'
import { useDeleteKit, useKits, useProducts, useSaveKit } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum } from '../lib/format'
import type { Kit } from '../lib/types'

type CompRow = { product_id: string; qty: number }
const emptyForm = () => ({
  sku: '',
  nome: '',
  ativo: true,
  preco_referencia: '',
  components: [{ product_id: '', qty: 1 }] as CompRow[],
})

export default function Kits() {
  const { data: kits, isLoading } = useKits()
  const { data: products } = useProducts()
  const save = useSaveKit()
  const del = useDeleteKit()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Kit | null>(null)
  const [form, setForm] = useState<any>(emptyForm())
  const [err, setErr] = useState('')

  function openNew() {
    setEditing(null)
    setForm(emptyForm())
    setErr('')
    setOpen(true)
  }
  function openEdit(k: Kit) {
    setEditing(k)
    setForm({
      sku: k.sku,
      nome: k.nome,
      ativo: k.ativo,
      preco_referencia: k.preco_referencia ?? '',
      components: k.components.length
        ? k.components.map((c) => ({ product_id: String(c.product_id), qty: c.qty }))
        : [{ product_id: '', qty: 1 }],
    })
    setErr('')
    setOpen(true)
  }

  const set = (k: string) => (e: any) =>
    setForm((f: any) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  function setComp(i: number, key: keyof CompRow, value: string) {
    setForm((f: any) => {
      const components = [...f.components]
      components[i] = { ...components[i], [key]: value }
      return { ...f, components }
    })
  }
  const addComp = () =>
    setForm((f: any) => ({ ...f, components: [...f.components, { product_id: '', qty: 1 }] }))
  const removeComp = (i: number) =>
    setForm((f: any) => ({ ...f, components: f.components.filter((_: any, j: number) => j !== i) }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    const components = form.components
      .filter((c: CompRow) => c.product_id)
      .map((c: CompRow) => ({ product_id: Number(c.product_id), qty: Number(c.qty) }))
    if (!components.length) {
      setErr('Adicione ao menos um componente')
      return
    }
    try {
      await save.mutateAsync({
        id: editing?.id,
        sku: form.sku,
        nome: form.nome,
        ativo: form.ativo,
        preco_referencia: form.preco_referencia === '' ? null : Number(form.preco_referencia),
        components,
      })
      setOpen(false)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function remove(k: Kit) {
    if (!confirm(`Excluir o kit "${k.nome}"?`)) return
    try {
      await del.mutateAsync(k.id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Kits</div>
          <div className="page-sub">Combinações vendáveis. O custo é a soma dos componentes.</div>
        </div>
        <button className="btn" onClick={openNew} disabled={!products?.length}>
          + Novo kit
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
                <th>Nome</th>
                <th>Composição</th>
                <th className="num">Itens</th>
                <th className="num">Custo atual</th>
                <th className="num">Estoque possível</th>
                <th>Ativo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {kits?.map((k) => (
                <tr key={k.id}>
                  <td>{k.sku}</td>
                  <td>{k.nome}</td>
                  <td>
                    {k.components.map((c, i) => (
                      <span className="pill" key={i}>
                        {c.qty}× {c.produto}
                      </span>
                    ))}
                  </td>
                  <td className="num">{fmtNum(k.qtd_itens)}</td>
                  <td className="num">{fmtBRL(k.custo_atual)}</td>
                  <td className="num">{fmtNum(k.estoque_possivel)}</td>
                  <td>
                    <span className={`badge ${k.ativo ? 'on' : 'off'}`}>{k.ativo ? 'Sim' : 'Não'}</span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost sm" onClick={() => openEdit(k)}>
                        Editar
                      </button>
                      <button className="btn ghost sm neg" onClick={() => remove(k)}>
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!kits?.length && (
                <tr>
                  <td colSpan={8} className="center-msg">
                    Nenhum kit cadastrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <Modal title={editing ? 'Editar kit' : 'Novo kit'} onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label>SKU do kit</label>
                <input value={form.sku} onChange={set('sku')} required />
              </div>
              <div className="field">
                <label>Nome do kit</label>
                <input value={form.nome} onChange={set('nome')} required />
              </div>
              <div className="field">
                <label>Preço de referência (R$)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.preco_referencia}
                  onChange={set('preco_referencia')}
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

            <label>Composição</label>
            {form.components.map((c: CompRow, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <select
                  value={c.product_id}
                  onChange={(e) => setComp(i, 'product_id', e.target.value)}
                  style={{ flex: 3 }}
                >
                  <option value="">Produto…</option>
                  {products?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.dropdown_name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={1}
                  value={c.qty}
                  onChange={(e) => setComp(i, 'qty', e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn secondary sm"
                  onClick={() => removeComp(i)}
                  disabled={form.components.length === 1}
                >
                  ✕
                </button>
              </div>
            ))}
            <button type="button" className="btn secondary sm" onClick={addComp}>
              + Componente
            </button>

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
