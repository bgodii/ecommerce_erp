import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import PeriodPicker from '../components/PeriodPicker'
import { api } from '../lib/api'
import { fmtBRL, fmtNum, fmtPct } from '../lib/format'
import { PERIOD_PRESETS } from '../lib/periods'

const useOverview = (from: string, to: string) =>
  useQuery({
    queryKey: ['visao-geral', from, to],
    queryFn: async () =>
      (await api.get('/reports/visao-geral', { params: { from, to } })).data,
  })

function Delta({ v }: { v: number | null }) {
  if (v == null) return null
  const pos = v >= 0
  return (
    <span className={pos ? 'pos' : 'neg'} style={{ fontSize: 12, fontWeight: 700 }}>
      {pos ? '▲' : '▼'} {Math.abs(v * 100).toFixed(0)}%
    </span>
  )
}

function Kpi({ label, value, delta, cls }: { label: string; value: string; delta?: number | null; cls?: string }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className={`value ${cls ?? ''}`} style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
        {value} {delta !== undefined && <Delta v={delta} />}
      </div>
    </div>
  )
}

const COST_COLORS: Record<string, string> = {
  cmv: '#6b7684',
  taxas_canal: '#c77812',
  ads: '#1f6fb5',
  lucro: '#12924e',
}
const COST_LABELS: Record<string, string> = {
  cmv: 'Produto (CMV)',
  taxas_canal: 'Taxas do canal',
  ads: 'Anúncios',
  lucro: 'Fica com você',
}

function BarChart({ data }: { data: { data: string; receita: number; lucro: number }[] }) {
  if (!data.length) return <p className="muted">Sem vendas no período.</p>
  const W = Math.max(420, data.length * 26)
  const H = 150
  const max = Math.max(...data.map((d) => d.receita), 1)
  const bw = W / data.length
  return (
    <div className="chart-wrap">
      <svg width={W} height={H + 22} role="img">
        {data.map((d, i) => {
          const hr = (d.receita / max) * H
          const hl = (Math.max(d.lucro, 0) / max) * H
          return (
            <g key={d.data}>
              <rect x={i * bw + 3} y={H - hr} width={bw - 6} height={hr} rx={3} fill="#f3c4b8" />
              <rect x={i * bw + 3} y={H - hl} width={bw - 6} height={hl} rx={3} fill="#ee4d2d" />
              {(i % Math.ceil(data.length / 8) === 0 || i === data.length - 1) && (
                <text x={i * bw + bw / 2} y={H + 15} textAnchor="middle" fontSize={9.5} fill="#98a1ad">
                  {d.data.slice(8, 10)}/{d.data.slice(5, 7)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <div className="cost-legend" style={{ marginTop: 4 }}>
        <span><span className="dot" style={{ background: '#f3c4b8' }} />Faturamento</span>
        <span><span className="dot" style={{ background: '#ee4d2d' }} />Lucro</span>
      </div>
    </div>
  )
}

export default function Home() {
  const [preset, setPreset] = useState('30d')
  const [period, setPeriod] = useState(PERIOD_PRESETS[1].calc())
  const { data: vg, isLoading } = useOverview(period.from, period.to)

  if (isLoading || !vg) return <div className="center-msg">Carregando sua visão geral…</div>

  const k = vg.kpis
  const c = vg.custos
  const custoParts = ['cmv', 'taxas_canal', 'ads', 'lucro'] as const
  const receita = Math.max(c.receita, 1)
  const semDados = k.faturamento === 0 && !vg.caixa.pedidos

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Visão geral</div>
          <div className="page-sub">Como sua loja está — sem mistério</div>
        </div>
        <PeriodPicker value={period} onChange={setPeriod} preset={preset} onPreset={setPreset} />
      </div>

      {semDados && (
        <div className="card" style={{ marginBottom: 18 }}>
          👋 Comece <Link className="link" to="/importar">importando os exports do seu marketplace</Link> —
          pedidos e ADS. Os produtos são criados automaticamente; depois é só registrar o estoque e o
          custo de compra em <Link className="link" to="/entradas">Entradas</Link>.
        </div>
      )}

      {!!vg.insights.length && (
        <>
          <h3 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span>🎯 O que fazer agora</span>
            <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>insights da sua operação</span>
          </h3>
          <div className="insights-row">
            {vg.insights.map((i: any, idx: number) => (
              <div key={idx} className={`insight ${i.tipo}`}>
                <span className="ic">{i.icone}</span>
                <div>
                  <b>{i.titulo}</b>
                  <p>{i.texto}</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="grid kpis">
        <Kpi label="Faturamento" value={fmtBRL(k.faturamento)} delta={k.delta_faturamento} />
        <Kpi label="Pedidos" value={fmtNum(k.pedidos)} />
        <Kpi label="Ticket médio" value={fmtBRL(k.ticket_medio)} />
        <Kpi label="Lucro (antes de ADS)" value={fmtBRL(k.lucro)} delta={k.delta_lucro} cls={k.lucro >= 0 ? 'pos' : 'neg'} />
        <Kpi label="Lucro após ADS" value={fmtBRL(k.lucro_apos_ads)} cls={k.lucro_apos_ads >= 0 ? 'pos' : 'neg'} />
        <Kpi label="Margem" value={fmtPct(k.margem)} />
        <Kpi label="ROAS (anúncios)" value={vg.ads.roas ? `${fmtNum(vg.ads.roas, 2)}×` : '—'} />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3>💰 Pra onde o dinheiro vai</h3>
          <div className="costbar">
            {custoParts.map((p) => (
              <div
                key={p}
                title={COST_LABELS[p]}
                style={{ width: `${Math.max((c[p] / receita) * 100, 0)}%`, background: COST_COLORS[p] }}
              />
            ))}
          </div>
          <div className="cost-legend">
            {custoParts.map((p) => (
              <span key={p}>
                <span className="dot" style={{ background: COST_COLORS[p] }} />
                {COST_LABELS[p]}: <b>{fmtBRL(c[p])}</b> ({((c[p] / receita) * 100).toFixed(0)}%)
              </span>
            ))}
          </div>
          {c.fonte_ads === 'manual' && (
            <p className="status-line">ADS via lançamentos manuais — importe os relatórios p/ dados por anúncio.</p>
          )}
        </div>

        <div className="card">
          <h3>🏦 Caixa do período</h3>
          <table>
            <tbody>
              <tr>
                <td className="muted">✅ Já entrou (pedidos concluídos)</td>
                <td className="num pos" style={{ fontWeight: 700 }}>{fmtBRL(vg.caixa.recebido)}</td>
              </tr>
              <tr>
                <td className="muted">🚚 Vai entrar (enviados/entregues)</td>
                <td className="num" style={{ fontWeight: 700 }}>{fmtBRL(vg.caixa.a_receber)}</td>
              </tr>
              <tr>
                <td className="muted">⏳ Aguardando pagamento</td>
                <td className="num">{fmtBRL(vg.caixa.aguardando_pagamento)}</td>
              </tr>
              <tr>
                <td className="muted">❌ Cancelados</td>
                <td className="num neg">
                  {fmtNum(vg.caixa.pedidos_cancelados)} pedido(s) ({fmtPct(vg.caixa.taxa_cancelamento, 0)})
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>📈 Vendas no período</h3>
        <BarChart data={vg.series_diaria} />
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div>
          <h3>🔥 Mais vendidos</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Produto</th><th className="num">Un.</th><th className="num">Receita</th></tr>
              </thead>
              <tbody>
                {vg.top_vendas.map((t: any) => (
                  <tr key={t.sku}>
                    <td style={{ whiteSpace: 'normal' }}>{t.nome}</td>
                    <td className="num">{fmtNum(t.unidades)}</td>
                    <td className="num">{fmtBRL(t.receita)}</td>
                  </tr>
                ))}
                {!vg.top_vendas.length && <tr><td colSpan={3} className="center-msg">Sem vendas.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3>💎 Mais lucrativos</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Produto</th><th className="num">Lucro</th><th className="num">Margem</th></tr>
              </thead>
              <tbody>
                {vg.top_lucro.map((t: any) => (
                  <tr key={t.sku}>
                    <td style={{ whiteSpace: 'normal' }}>{t.nome}</td>
                    <td className={`num ${t.lucro >= 0 ? 'pos' : 'neg'}`}>{fmtBRL(t.lucro)}</td>
                    <td className="num">{fmtPct(t.margem)}</td>
                  </tr>
                ))}
                {!vg.top_lucro.length && <tr><td colSpan={3} className="center-msg">Sem vendas.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {!!vg.ads_produtos.length && (
        <>
          <h3 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span>📣 Seus anúncios valem a pena?</span>
            <Link className="link" to="/analise-ads" style={{ fontSize: 13 }}>ver análise completa →</Link>
          </h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Anúncio</th>
                  <th className="num">Investido</th>
                  <th className="num">Vendeu (GMV)</th>
                  <th className="num">ROAS</th>
                  <th className="num">Mínimo p/ lucrar</th>
                  <th>Veredito</th>
                </tr>
              </thead>
              <tbody>
                {vg.ads_produtos.slice(0, 5).map((p: any) => (
                  <tr key={p.listing + p.nome}>
                    <td style={{ whiteSpace: 'normal', maxWidth: 380 }}>{p.nome}</td>
                    <td className="num">{fmtBRL(p.spend)}</td>
                    <td className="num">{fmtBRL(p.gmv)}</td>
                    <td className="num" style={{ fontWeight: 700 }}>{fmtNum(p.roas, 2)}×</td>
                    <td className="num">{p.roas_equilibrio ? `${fmtNum(p.roas_equilibrio, 2)}×` : '—'}</td>
                    <td><span className={`verdict ${p.veredito}`}>{p.veredito}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  )
}
