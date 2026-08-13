import { useDashboard } from '../hooks/queries'
import { fmtBRL, fmtNum } from '../lib/format'

function Kpi({ label, value, cls = '' }: { label: string; value: string; cls?: string }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className={`value ${cls}`}>{value}</div>
    </div>
  )
}

export default function Dashboard() {
  const { data: d, isLoading } = useDashboard()
  if (isLoading || !d) return <div className="center-msg">Carregando…</div>
  const sign = (n: number) => (n >= 0 ? 'pos' : 'neg')

  return (
    <>
      <div className="page-title">Dashboard</div>
      <div className="page-sub">Estoque, vendas e resultado da sua loja</div>

      <div className="grid kpis">
        <Kpi label="Estoque total" value={`${fmtNum(d.estoque_total)} un`} />
        <Kpi label="Valor do estoque" value={fmtBRL(d.valor_estoque)} />
        <Kpi label="Receita bruta" value={fmtBRL(d.receita_bruta)} />
        <Kpi label="Taxas totais" value={fmtBRL(d.taxas_totais)} />
        <Kpi label="Receita líquida" value={fmtBRL(d.receita_liquida)} />
        <Kpi label="CMV (FIFO)" value={fmtBRL(d.cmv)} />
        <Kpi label="Lucro antes de Ads" value={fmtBRL(d.lucro_antes_ads)} cls={sign(d.lucro_antes_ads)} />
        <Kpi label="Total em Ads" value={fmtBRL(d.ads_total)} />
        <Kpi label="Lucro após Ads" value={fmtBRL(d.lucro_apos_ads)} cls={sign(d.lucro_apos_ads)} />
      </div>

      <div className="grid split">
        <div>
          <h3>Estoque por produto</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th className="num">Estoque</th>
                  <th className="num">Valor</th>
                  <th className="num">Custo médio</th>
                </tr>
              </thead>
              <tbody>
                {d.produtos.map((p, i) => (
                  <tr key={i}>
                    <td>{p.dropdown_name}</td>
                    <td className="num">{fmtNum(p.estoque)}</td>
                    <td className="num">{fmtBRL(p.valor_estoque)}</td>
                    <td className="num">{fmtBRL(p.custo_medio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3>Estoque possível de kits</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Kit</th>
                  <th className="num">Possível</th>
                </tr>
              </thead>
              <tbody>
                {d.kits.map((k, i) => (
                  <tr key={i}>
                    <td>{k.nome}</td>
                    <td className="num">{fmtNum(k.estoque_possivel)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
