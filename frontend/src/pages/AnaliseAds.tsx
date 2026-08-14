import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { SortTh, useSort } from '../components/Sortable'
import { api } from '../lib/api'
import { fmtBRL, fmtNum, todayISO } from '../lib/format'

const daysAgoISO = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const VERDICT_HELP: Record<string, string> = {
  escalar: 'ROAS bem acima do mínimo — vale aumentar o investimento',
  ok: 'Acima do mínimo — mantém',
  atencao: 'Abaixo do mínimo — está corroendo a margem',
  pausar: 'Muito abaixo / sem conversão — considere pausar',
}

interface AdRow {
  listing: string
  nome: string
  spend: number
  gmv: number
  itens_vendidos: number
  roas: number
  roas_equilibrio: number | null
  veredito: string
}

export default function AnaliseAds() {
  const [from, setFrom] = useState(daysAgoISO(29))
  const [to, setTo] = useState(todayISO())
  const { data: vg, isLoading } = useQuery({
    queryKey: ['visao-geral', from, to],
    queryFn: async () => (await api.get('/reports/visao-geral', { params: { from, to } })).data,
  })
  const rows: AdRow[] = vg?.ads_produtos ?? []
  const sort = useSort<AdRow>(rows, 'spend', 'desc')

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Análise de ADS</div>
          <div className="page-sub">
            ROAS real por anúncio vs o mínimo pra lucrar (1 ÷ margem). Dados dos relatórios importados.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <button className="btn secondary sm" onClick={() => { setFrom(daysAgoISO(6)); setTo(todayISO()) }}>7 dias</button>
          <button className="btn secondary sm" onClick={() => { setFrom(daysAgoISO(29)); setTo(todayISO()) }}>30 dias</button>
          <div className="field" style={{ margin: 0 }}>
            <label>De</label>
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label>Até</label>
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
        </div>
      </div>

      {vg && (
        <div className="grid kpis">
          <div className="card kpi">
            <div className="label">Investimento no período</div>
            <div className="value">{fmtBRL(vg.ads.spend)}</div>
          </div>
          <div className="card kpi">
            <div className="label">GMV dos anúncios</div>
            <div className="value">{fmtBRL(vg.ads.gmv_anunciado)}</div>
          </div>
          <div className="card kpi">
            <div className="label">ROAS médio</div>
            <div className="value">{vg.ads.roas ? `${fmtNum(vg.ads.roas, 2)}×` : '—'}</div>
          </div>
          <div className="card kpi">
            <div className="label">% do faturamento</div>
            <div className="value">{fmtNum(vg.ads.pct_faturamento * 100, 1)}%</div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : !rows.length ? (
        <div className="card">
          Nenhum relatório de ADS cobre este período.{' '}
          <Link className="link" to="/importar">Importar relatórios →</Link>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Anúncio / Produto</th>
                <SortTh<AdRow> label="Investido" k="spend" sort={sort} num />
                <SortTh<AdRow> label="GMV" k="gmv" sort={sort} num />
                <SortTh<AdRow> label="Itens" k="itens_vendidos" sort={sort} num />
                <SortTh<AdRow> label="ROAS" k="roas" sort={sort} num />
                <th className="num">Mínimo p/ lucrar</th>
                <th>Veredito</th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((p) => (
                <tr key={p.listing + p.nome}>
                  <td style={{ whiteSpace: 'normal', maxWidth: 420 }}>{p.nome}</td>
                  <td className="num">{fmtBRL(p.spend)}</td>
                  <td className="num">{fmtBRL(p.gmv)}</td>
                  <td className="num">{fmtNum(p.itens_vendidos)}</td>
                  <td className="num" style={{ fontWeight: 700 }}>{fmtNum(p.roas, 2)}×</td>
                  <td className="num">{p.roas_equilibrio ? `${fmtNum(p.roas_equilibrio, 2)}×` : '—'}</td>
                  <td>
                    <span className={`verdict ${p.veredito}`} title={VERDICT_HELP[p.veredito]}>
                      {p.veredito}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="status-line" style={{ marginTop: 10 }}>
        O "mínimo p/ lucrar" usa a margem média da loja no período. Vereditos: escalar · ok · atenção · pausar.
      </p>
    </>
  )
}
