import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import PeriodPicker from '../components/PeriodPicker'
import { SortTh, useSort } from '../components/Sortable'
import Th from '../components/Th'
import { api } from '../lib/api'
import { fmtBRL, fmtNum, fmtPct } from '../lib/format'
import { PERIOD_PRESETS } from '../lib/periods'

const VERDICT_HELP: Record<string, string> = {
  escalar: 'ROAS bem acima do even — vale aumentar o investimento',
  ok: 'Acima do ROAS even — mantém',
  atencao: 'Abaixo do ROAS even — está corroendo a margem',
  pausar: 'Muito abaixo / sem conversão — considere pausar',
}

interface AdRow {
  listing: string
  nome: string
  spend: number
  gmv: number
  itens_vendidos: number
  roas: number
  roas_even: number | null
  lucro_estimado: number | null
  veredito: string
}

export default function AnaliseAds() {
  const [preset, setPreset] = useState('30d')
  const [period, setPeriod] = useState(PERIOD_PRESETS[1].calc())
  const { data: vg, isLoading } = useQuery({
    queryKey: ['visao-geral', period.from, period.to],
    queryFn: async () =>
      (await api.get('/reports/visao-geral', { params: { from: period.from, to: period.to } })).data,
  })
  const rows: AdRow[] = vg?.ads_produtos ?? []
  const sort = useSort<AdRow>(rows, 'spend', 'desc')
  const roasEven = vg?.ads?.roas_even ?? null

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Análise de ADS</div>
          <div className="page-sub">
            ROAS real de cada anúncio comparado ao <b>ROAS even</b> — o mínimo pra não ter prejuízo.
          </div>
        </div>
        <PeriodPicker value={period} onChange={setPeriod} preset={preset} onPreset={setPreset} />
      </div>

      {vg && (
        <>
          <div className="grid kpis">
            <div className="card kpi">
              <div className="label">ROAS even (mínimo)</div>
              <div className="value">{roasEven ? `${fmtNum(roasEven, 2)}×` : '—'}</div>
              <div className="status-line" style={{ margin: 0 }}>
                = 1 ÷ margem ({fmtPct(vg.ads.margem_base)})
              </div>
            </div>
            <div className="card kpi">
              <div className="label">ROAS médio</div>
              <div className={`value ${roasEven && vg.ads.roas >= roasEven ? 'pos' : 'neg'}`}>
                {vg.ads.roas ? `${fmtNum(vg.ads.roas, 2)}×` : '—'}
              </div>
            </div>
            <div className="card kpi">
              <div className="label">Investimento</div>
              <div className="value">{fmtBRL(vg.ads.spend)}</div>
            </div>
            <div className="card kpi">
              <div className="label">GMV dos anúncios</div>
              <div className="value">{fmtBRL(vg.ads.gmv_anunciado)}</div>
            </div>
            <div className="card kpi">
              <div className="label">% do faturamento</div>
              <div className="value">{fmtNum(vg.ads.pct_faturamento * 100, 1)}%</div>
            </div>
          </div>

          {roasEven && (
            <div className={`insight ${vg.ads.roas >= roasEven ? 'sucesso' : 'alerta'}`} style={{ marginBottom: 18 }}>
              <span className="ic">{vg.ads.roas >= roasEven ? '✅' : '⚠️'}</span>
              <div>
                <b>
                  {vg.ads.roas >= roasEven
                    ? `Seus anúncios estão no lucro (ROAS ${fmtNum(vg.ads.roas, 2)}× vs even ${fmtNum(roasEven, 2)}×)`
                    : `Seus anúncios estão no prejuízo (ROAS ${fmtNum(vg.ads.roas, 2)}× abaixo do even ${fmtNum(roasEven, 2)}×)`}
                </b>
                <p>
                  Com margem de {fmtPct(vg.ads.margem_base)}, cada R$ 1 investido precisa gerar pelo
                  menos R$ {fmtNum(roasEven, 2)} de venda para empatar.
                </p>
              </div>
            </div>
          )}
        </>
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
                <Th label="Anúncio / Produto" help="Nome do anúncio no marketplace" />
                <SortTh<AdRow> label="Investido" k="spend" sort={sort} num help="Quanto você gastou neste anúncio no período" />
                <SortTh<AdRow> label="GMV" k="gmv" sort={sort} num help="Valor vendido atribuído a este anúncio" />
                <SortTh<AdRow> label="Itens" k="itens_vendidos" sort={sort} num help="Unidades vendidas pelo anúncio" />
                <SortTh<AdRow> label="ROAS" k="roas" sort={sort} num help="Retorno real: GMV ÷ investido. Quanto vendeu por real gasto." />
                <SortTh<AdRow> label="ROAS even" k="roas_even" sort={sort} num help="Ponto de equilíbrio (1 ÷ margem): abaixo disso o anúncio dá prejuízo" />
                <SortTh<AdRow> label="Lucro estim." k="lucro_estimado" sort={sort} num help="GMV × margem − investido. Estimativa do que sobrou depois do anúncio." />
                <Th label="Veredito" help="escalar = muito acima do even · ok = acima · atenção = abaixo · pausar = bem abaixo ou sem vendas" />
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((p) => {
                const acima = p.roas_even != null && p.roas >= p.roas_even
                return (
                  <tr key={p.listing + p.nome}>
                    <td style={{ whiteSpace: 'normal', maxWidth: 400 }}>{p.nome}</td>
                    <td className="num">{fmtBRL(p.spend)}</td>
                    <td className="num">{fmtBRL(p.gmv)}</td>
                    <td className="num">{fmtNum(p.itens_vendidos)}</td>
                    <td className={`num ${acima ? 'pos' : 'neg'}`} style={{ fontWeight: 700 }}>
                      {fmtNum(p.roas, 2)}×
                    </td>
                    <td className="num muted">{p.roas_even ? `${fmtNum(p.roas_even, 2)}×` : '—'}</td>
                    <td className={`num ${(p.lucro_estimado ?? 0) >= 0 ? 'pos' : 'neg'}`}>
                      {p.lucro_estimado != null ? fmtBRL(p.lucro_estimado) : '—'}
                    </td>
                    <td>
                      <span className={`verdict ${p.veredito}`} title={VERDICT_HELP[p.veredito]}>
                        {p.veredito}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="status-line" style={{ marginTop: 10 }}>
        <b>ROAS even</b> = 1 ÷ margem líquida da loja no período. Acima dele o anúncio dá lucro;
        abaixo, consome mais do que a margem gera. "Lucro estim." = GMV × margem − investimento.
      </p>
    </>
  )
}
