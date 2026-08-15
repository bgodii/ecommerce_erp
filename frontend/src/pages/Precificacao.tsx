import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import Th from '../components/Th'
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
    taxa_conversao: 1, // % esperado de conversão do anúncio
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
        taxa_conversao: Number(form.taxa_conversao) > 0 ? Number(form.taxa_conversao) / 100 : null,
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
              <div className="field">
                <label>Conversão esperada do anúncio (%)</label>
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={form.taxa_conversao}
                  onChange={set('taxa_conversao')}
                  title="A cada 100 cliques, quantas viram venda. Use o número real da sua Análise de ADS."
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
                <Row label="Comissão do canal" value={fmtBRL(res.taxa_shopee_rs)} />
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

      {res && !res.erro && res.roas_even && (
        <>
          <h3 style={{ marginTop: 20 }}>📣 Metas de anúncio para este preço</h3>
          <div className="grid kpis">
            <div className="card kpi">
              <div className="label">ROAS even (mínimo)</div>
              <div className="value">{fmtNum(res.roas_even, 2)}×</div>
              <div className="status-line" style={{ margin: 0 }}>
                = 1 ÷ margem ({fmtPct(res.margem)})
              </div>
            </div>
            <div className="card kpi">
              <div className="label">Margem por venda</div>
              <div className="value pos">{fmtBRL(res.margem_por_venda)}</div>
              <div className="status-line" style={{ margin: 0 }}>
                é o que você pode gastar em ads por venda
              </div>
            </div>
            {res.cpc_alvo && (
              <div className="card kpi">
                <div className="label">CPC máximo ({fmtNum(res.cpc_alvo.taxa_conversao * 100, 1)}% conv.)</div>
                <div className="value">{fmtBRL(res.cpc_alvo.cpc_maximo)}</div>
                <div className="status-line" style={{ margin: 0 }}>
                  {res.cpc_alvo.cliques_por_venda} cliques por venda
                </div>
              </div>
            )}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <Th label="Se a conversão for…" help="Percentual de cliques que viram venda" />
                  <Th label="Cliques por venda" help="Quantos cliques você paga até sair uma venda (1 ÷ conversão)" num />
                  <Th label="CPC máximo" help="Teto que o clique pode custar: margem da venda × taxa de conversão" num />
                  <Th label="Gasto máx. por venda" help="Quanto de anúncio cabe em uma venda sem dar prejuízo (= margem por venda)" num />
                </tr>
              </thead>
              <tbody>
                {res.metas_cpc?.map((m: any) => (
                  <tr
                    key={m.taxa_conversao}
                    className={
                      res.cpc_alvo && Math.abs(m.taxa_conversao - res.cpc_alvo.taxa_conversao) < 1e-9
                        ? 'row-selected'
                        : ''
                    }
                  >
                    <td>{fmtNum(m.taxa_conversao * 100, 1)}%</td>
                    <td className="num">{m.cliques_por_venda}</td>
                    <td className="num" style={{ fontWeight: 700 }}>{fmtBRL(m.cpc_maximo)}</td>
                    <td className="num">{fmtBRL(res.margem_por_venda)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="status-line">
            Quanto pior a conversão, <b>menos</b> você pode pagar por clique. Compare o CPC máximo
            com o CPC real de cada anúncio em <Link className="link" to="/analise-ads">Análise de ADS</Link>.
          </p>
        </>
      )}
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
