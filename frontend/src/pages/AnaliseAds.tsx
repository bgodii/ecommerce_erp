import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useRoasMarginal } from '../hooks/queries'
import PeriodPicker from '../components/PeriodPicker'
import { SortTh, useSort } from '../components/Sortable'
import Th from '../components/Th'
import { api } from '../lib/api'
import { fmtBRL, fmtNum, fmtPct } from '../lib/format'
import { DEFAULT_PRESET, PERIOD_PRESETS } from '../lib/periods'

const VERDICT_INFO: Record<string, { label: string; resumo: string; oQueFazer: string }> = {
  escalar: {
    label: 'escalar',
    resumo: 'Vende pelo menos 50% acima do necessário para empatar',
    oQueFazer: 'Está sobrando margem. Aumente o orçamento aos poucos (20–30% por vez) e acompanhe se o ROAS se mantém.',
  },
  ok: {
    label: 'ok',
    resumo: 'Passa do ponto de equilíbrio, mas sem folga grande',
    oQueFazer: 'Dá lucro. Mantenha o orçamento. Para escalar sem risco, melhore antes a conversão (preço, fotos, avaliações).',
  },
  atencao: {
    label: 'atenção',
    resumo: 'Abaixo do equilíbrio — o anúncio come parte da sua margem',
    oQueFazer: 'Ainda vende, mas o lucro está indo para o anúncio. Reduza o lance/CPC ou melhore a conversão. Se não melhorar, pause.',
  },
  pausar: {
    label: 'pausar',
    resumo: 'Muito abaixo do equilíbrio ou gastou sem vender',
    oQueFazer: 'Está queimando dinheiro. Pause e revise o anúncio (título, foto, preço) antes de reativar.',
  },
}
const VERDICT_HELP: Record<string, string> = Object.fromEntries(
  Object.entries(VERDICT_INFO).map(([k, v]) => [k, `${v.resumo}. ${v.oQueFazer}`]),
)

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
  // funil de cliques
  impressoes: number
  cliques: number
  conversoes: number
  ctr: number
  cpc: number
  taxa_conversao: number
  faixa_conversao: string
  cliques_por_venda: number | null
  custo_por_venda: number | null
  cpc_maximo: number | null
  cliques_maximos_por_venda: number | null
  cpc_saudavel: boolean | null
}

const FAIXA_CONV: Record<string, { label: string; cls: string }> = {
  otima: { label: 'ótima', cls: 'escalar' },
  boa: { label: 'boa', cls: 'ok' },
  atencao: { label: 'baixa', cls: 'atencao' },
  ruim: { label: 'ruim', cls: 'pausar' },
  sem_dados: { label: '—', cls: 'ok' },
}

export default function AnaliseAds() {
  const [preset, setPreset] = useState('30d')
  const [period, setPeriod] = useState(PERIOD_PRESETS[DEFAULT_PRESET].calc())
  const { data: vg, isLoading } = useQuery({
    queryKey: ['visao-geral', period.from, period.to],
    queryFn: async () =>
      (await api.get('/reports/visao-geral', { params: { from: period.from, to: period.to } })).data,
  })
  const { data: mg } = useRoasMarginal(7)
  const [aba, setAba] = useState<'resultado' | 'cliques'>('resultado')
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

      {vg && vg.ads.fonte === 'importado' && !vg.ads.exato && (
        <div className="insight info" style={{ marginBottom: 14 }}>
          <span className="ic">📐</span>
          <div>
            <b>Números de ADS estimados para este filtro</b>
            <p>
              A Shopee exporta os anúncios <b>agregados por período</b>, sem quebra por dia. Seus
              relatórios cobrem{' '}
              {vg.ads.cobertura.map((c: any) => `${c.de} a ${c.ate}`).join(', ')} — para o filtro
              escolhido, os valores foram <b>rateados proporcionalmente aos dias</b>. Para números
              exatos por semana, exporte um relatório por semana na Shopee.
            </p>
          </div>
        </div>
      )}

      {mg && (
        <div className="card" style={{ marginBottom: 18 }}>
          <h3>📊 Devo escalar? (ROAS marginal — 7 dias vs 7 anteriores)</h3>
          <div className="table-wrap" style={{ marginBottom: 10 }}>
            <table>
              <thead>
                <tr>
                  <Th label="Período" help="Janelas comparadas" />
                  <Th label="Investido" help="Gasto em anúncios na janela" num />
                  <Th label="GMV" help="Valor vendido atribuído aos anúncios" num />
                  <Th label="ROAS médio" help="GMV ÷ investido de toda a janela" num />
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Anterior ({mg.anterior.de} a {mg.anterior.ate})</td>
                  <td className="num">{fmtBRL(mg.anterior.spend)}</td>
                  <td className="num">{fmtBRL(mg.anterior.gmv)}</td>
                  <td className="num">{fmtNum(mg.anterior.roas, 2)}×</td>
                </tr>
                <tr>
                  <td><b>Atual ({mg.atual.de} a {mg.atual.ate})</b></td>
                  <td className="num"><b>{fmtBRL(mg.atual.spend)}</b></td>
                  <td className="num"><b>{fmtBRL(mg.atual.gmv)}</b></td>
                  <td className="num"><b>{fmtNum(mg.atual.roas, 2)}×</b></td>
                </tr>
                <tr className="row-selected">
                  <td><b>Diferença (o dinheiro extra)</b></td>
                  <td className="num">{fmtBRL(mg.delta_spend)}</td>
                  <td className="num">{fmtBRL(mg.delta_gmv)}</td>
                  <td className="num" style={{ fontWeight: 700 }}>
                    {mg.roas_marginal != null ? `${fmtNum(mg.roas_marginal, 2)}× marginal` : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div
            className={`insight ${
              mg.veredito === 'escalar' ? 'sucesso' : mg.veredito === 'voltar' ? 'alerta' : 'info'
            }`}
          >
            <span className="ic">
              {mg.veredito === 'escalar' ? '🚀' : mg.veredito === 'voltar' ? '🛑' : mg.veredito === 'no_limite' ? '🎯' : 'ℹ️'}
            </span>
            <div>
              <b>
                {mg.veredito === 'escalar' && 'Pode escalar'}
                {mg.veredito === 'no_limite' && 'Você está no ponto de lucro máximo'}
                {mg.veredito === 'voltar' && 'Volte o orçamento'}
                {mg.veredito === 'sem_aumento' && 'Sem aumento para avaliar'}
                {mg.veredito === 'sem_dados' && 'Dados insuficientes'}
                {mg.veredito === 'sem_margem' && 'Falta cadastrar custos'}
              </b>
              <p>{mg.recomendacao}</p>
            </div>
          </div>
          <p className="status-line">
            O <b>ROAS marginal</b> é o retorno do dinheiro que você adicionou — e não a média.
            Enquanto ele ficar acima do ROAS even ({mg.roas_even ? `${fmtNum(mg.roas_even, 2)}×` : '—'}),
            aumentar o investimento ainda gera lucro; abaixo dele, cada real a mais reduz seu lucro
            mesmo que a média continue bonita.
          </p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button
          className={`btn sm ${aba === 'resultado' ? '' : 'secondary'}`}
          onClick={() => setAba('resultado')}
        >
          💰 Resultado
        </button>
        <button
          className={`btn sm ${aba === 'cliques' ? '' : 'secondary'}`}
          onClick={() => setAba('cliques')}
        >
          🖱️ Funil de cliques
        </button>
      </div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : !rows.length ? (
        <div className="card">
          Nenhum relatório de ADS cobre este período.{' '}
          <Link className="link" to="/importar">Importar relatórios →</Link>
        </div>
      ) : aba === 'resultado' ? (
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
                <Th label="Veredito" help="Comparação do ROAS real com o ROAS even. Veja a legenda abaixo da tabela." />
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
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <Th label="Anúncio / Produto" help="Nome do anúncio no marketplace" />
                <SortTh<AdRow> label="Impressões" k="impressoes" sort={sort} num help="Quantas vezes o anúncio apareceu" />
                <SortTh<AdRow> label="Cliques" k="cliques" sort={sort} num help="Quantas pessoas clicaram" />
                <SortTh<AdRow> label="CTR" k="ctr" sort={sort} num help="Cliques ÷ impressões. Mede se o anúncio chama atenção." />
                <SortTh<AdRow> label="Conversão" k="taxa_conversao" sort={sort} num help="Vendas ÷ cliques. Mede se a página convence quem clicou." />
                <SortTh<AdRow> label="Cliq/venda" k="cliques_por_venda" sort={sort} num help="Quantos cliques você paga até sair uma venda" />
                <SortTh<AdRow> label="Máx. cliq/venda" k="cliques_maximos_por_venda" sort={sort} num help="Quantos cliques você PODE pagar por venda sem prejuízo (margem da venda ÷ CPC)" />
                <SortTh<AdRow> label="CPC" k="cpc" sort={sort} num help="Custo por clique: investido ÷ cliques" />
                <SortTh<AdRow> label="CPC máx." k="cpc_maximo" sort={sort} num help="Teto do clique: (ticket × margem) ÷ cliques por venda. Acima disso o anúncio dá prejuízo." />
                <SortTh<AdRow> label="Custo/venda" k="custo_por_venda" sort={sort} num help="Quanto de anúncio custou cada venda" />
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((p) => {
                const f = FAIXA_CONV[p.faixa_conversao] ?? FAIXA_CONV.sem_dados
                return (
                  <tr key={p.listing + p.nome}>
                    <td style={{ whiteSpace: 'normal', maxWidth: 320 }}>{p.nome}</td>
                    <td className="num">{fmtNum(p.impressoes)}</td>
                    <td className="num">{fmtNum(p.cliques)}</td>
                    <td className="num">{fmtNum(p.ctr * 100, 2)}%</td>
                    <td className="num">
                      <span className={`verdict ${f.cls}`} title={`Faixa: ${f.label}`}>
                        {fmtNum(p.taxa_conversao * 100, 2)}%
                      </span>
                    </td>
                    <td className="num" style={{ fontWeight: 700 }}>
                      {p.cliques_por_venda != null ? fmtNum(p.cliques_por_venda, 0) : '—'}
                    </td>
                    <td className="num muted">
                      {p.cliques_maximos_por_venda != null ? fmtNum(p.cliques_maximos_por_venda, 0) : '—'}
                    </td>
                    <td className={`num ${p.cpc_saudavel === false ? 'neg' : ''}`} style={{ fontWeight: 700 }}>
                      {fmtBRL(p.cpc)}
                    </td>
                    <td className="num muted">{p.cpc_maximo != null ? fmtBRL(p.cpc_maximo) : '—'}</td>
                    <td className="num">{p.custo_por_venda != null ? fmtBRL(p.custo_por_venda) : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="status-line" style={{ marginTop: 10 }}>
        {aba === 'resultado' ? (
          <>
            <b>ROAS even</b> = 1 ÷ margem líquida. Acima dele o anúncio dá lucro; abaixo, consome mais
            do que a margem gera. "Lucro estim." = GMV × margem − investimento.
          </>
        ) : (
          <>
            <b>CPC máx.</b> = (ticket médio × margem) ÷ cliques por venda — o teto que cada clique pode
            custar. Se o <b>CPC</b> passar do teto (em vermelho), o anúncio queima mais do que a venda
            deixa. <b>Conversão</b>: ótima ≥2% · boa 1–2% · baixa 0,5–1% · ruim &lt;0,5%.
          </>
        )}
      </p>
      {aba === 'resultado' && (
        <div className="card" style={{ marginTop: 12 }}>
          <h3>O que significa cada veredito</h3>
          <table>
            <tbody>
              {Object.entries(VERDICT_INFO).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ width: 96 }}>
                    <span className={`verdict ${k}`}>{v.label}</span>
                  </td>
                  <td style={{ whiteSpace: 'normal' }}>
                    <b>{v.resumo}.</b>{' '}
                    <span className="muted">{v.oQueFazer}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
