import { FormEvent, useState } from 'react'
import { useChannels, useSimulatePricing } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum, fmtPct } from '../lib/format'

export default function Precificacao() {
  const sim = useSimulatePricing()
  const { data: channels } = useChannels()
  const [err, setErr] = useState('')
  const [form, setForm] = useState<any>({
    custo_unitario: 0,
    qty: 1,
    modo: 'lucro',
    channel_id: '',
    taxa_afiliado_pct: 0,
    outros_custos: 0,
    lucro_desejado: 10,
    preco_informado: 0,
  })
  const set = (k: string) => (e: any) => setForm((f: any) => ({ ...f, [k]: e.target.value }))
  const res = sim.data

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await sim.mutateAsync({
        custo_unitario: Number(form.custo_unitario),
        qty: Number(form.qty),
        modo: form.modo,
        channel_id: form.channel_id ? Number(form.channel_id) : null,
        taxa_afiliado_pct: Number(form.taxa_afiliado_pct) / 100,
        outros_custos: Number(form.outros_custos),
        lucro_desejado: form.modo === 'lucro' ? Number(form.lucro_desejado) : null,
        preco_informado: form.modo === 'preco' ? Number(form.preco_informado) : null,
      })
    } catch (e) {
      setErr(apiError(e))
    }
  }

  return (
    <>
      <div className="page-title">Precificação</div>
      <div className="page-sub">
        Defina o lucro desejado e descubra o preço — ou informe o preço e veja o lucro.
      </div>

      <div className="grid cols-2">
        <div className="card">
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="field">
                <label>E-commerce</label>
                <select value={form.channel_id} onChange={set('channel_id')}>
                  <option value="">Automático (1º ativo)</option>
                  {channels
                    ?.filter((c) => c.ativo)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              </div>
              <div className="field">
                <label>Custo unitário (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  value={form.custo_unitario}
                  onChange={set('custo_unitario')}
                  required
                  autoFocus
                />
              </div>
              <div className="field">
                <label>Quantidade no pedido</label>
                <input type="number" min={1} value={form.qty} onChange={set('qty')} />
              </div>
              <div className="field">
                <label>Modo de cálculo</label>
                <select value={form.modo} onChange={set('modo')}>
                  <option value="lucro">Quero definir o lucro</option>
                  <option value="preco">Quero informar o preço</option>
                </select>
              </div>
              {form.modo === 'lucro' ? (
                <div className="field">
                  <label>Lucro desejado (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.lucro_desejado}
                    onChange={set('lucro_desejado')}
                  />
                </div>
              ) : (
                <div className="field">
                  <label>Preço de venda (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.preco_informado}
                    onChange={set('preco_informado')}
                  />
                </div>
              )}
              <div className="field">
                <label>Taxa afiliado / extra (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.taxa_afiliado_pct}
                  onChange={set('taxa_afiliado_pct')}
                />
              </div>
              <div className="field">
                <label>Outros custos (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.outros_custos}
                  onChange={set('outros_custos')}
                />
              </div>
            </div>
            <p className="status-line">A taxa do marketplace e a taxa fixa vêm do e-commerce selecionado.</p>
            <button className="btn" disabled={sim.isPending}>
              {sim.isPending ? 'Calculando…' : 'Calcular'}
            </button>
          </form>
        </div>

        <div className="card">
          <h3>Resultado</h3>
          {!res ? (
            <p className="muted">Preencha e clique em Calcular.</p>
          ) : res.erro ? (
            <div className="error">{res.status}</div>
          ) : (
            <table>
              <tbody>
                <Row label="Custo unitário" value={fmtBRL(res.custo_unitario)} />
                <Row label="Preço unitário" value={fmtBRL(res.preco_unitario)} strong />
                <Row label="Receita bruta" value={fmtBRL(res.receita_bruta)} />
                <Row label="Taxa Shopee" value={fmtBRL(res.taxa_shopee_rs)} />
                <Row label="Taxa afiliado/extra" value={fmtBRL(res.taxa_afiliado_rs)} />
                <Row label="Taxa fixa" value={fmtBRL(res.taxa_fixa_rs)} />
                <Row label="Outros custos" value={fmtBRL(res.outros_custos)} />
                <Row label="CMV" value={fmtBRL(res.cmv)} />
                <Row label="Lucro do pedido" value={fmtBRL(res.lucro)} strong pos={(res.lucro ?? 0) >= 0} />
                <Row label="Lucro por unidade" value={fmtBRL(res.lucro_unitario)} />
                <Row label="Margem líquida" value={fmtPct(res.margem)} />
                <Row label="Preço de equilíbrio" value={fmtBRL(res.preco_equilibrio)} />
                <Row label="Markup sobre custo" value={`${fmtNum(res.markup, 2)}×`} />
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}

function Row({
  label,
  value,
  strong,
  pos,
}: {
  label: string
  value: string
  strong?: boolean
  pos?: boolean
}) {
  return (
    <tr>
      <td className="muted">{label}</td>
      <td className="num" style={{ fontWeight: strong ? 700 : 400 }}>
        <span className={pos === undefined ? '' : pos ? 'pos' : 'neg'}>{value}</span>
      </td>
    </tr>
  )
}
