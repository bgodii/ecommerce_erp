import { SortTh, useSort } from '../components/Sortable'
import { useBalanco } from '../hooks/queries'
import { fmtBRL, fmtDate, fmtNum, fmtPct } from '../lib/format'
import type { BalancoDia } from '../lib/types'

export default function BalancoDiario() {
  const { data, isLoading } = useBalanco()
  const sort = useSort<BalancoDia>(data, 'data', 'asc')

  return (
    <>
      <div className="page-title">Balanço Diário</div>
      <div className="page-sub">DRE por dia: receita, taxas, CMV, Ads, lucro, margem e ROAS</div>

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh<BalancoDia> label="Data" k="data" sort={sort} />
                <th className="num">Qtd</th>
                <th className="num">Receita</th>
                <th className="num">Taxa Shopee</th>
                <th className="num">Taxa fixa</th>
                <th className="num">Afiliado/Extra</th>
                <th className="num">Outras</th>
                <th className="num">Líquida</th>
                <th className="num">CMV</th>
                <th className="num">Ads</th>
                <th className="num">Lucro após Ads</th>
                <th className="num">Margem</th>
                <th className="num">ROAS</th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((b) => (
                <tr key={b.data}>
                  <td>{fmtDate(b.data)}</td>
                  <td className="num">{fmtNum(b.qty)}</td>
                  <td className="num">{fmtBRL(b.receita_bruta)}</td>
                  <td className="num">{fmtBRL(b.taxa_shopee)}</td>
                  <td className="num">{fmtBRL(b.taxa_fixa)}</td>
                  <td className="num">{fmtBRL(b.taxa_afiliado)}</td>
                  <td className="num">{fmtBRL(b.outras_taxas)}</td>
                  <td className="num">{fmtBRL(b.receita_liquida)}</td>
                  <td className="num">{fmtBRL(b.cmv)}</td>
                  <td className="num">{fmtBRL(b.ads)}</td>
                  <td className={`num ${b.lucro_apos_ads >= 0 ? 'pos' : 'neg'}`}>
                    {fmtBRL(b.lucro_apos_ads)}
                  </td>
                  <td className={`num ${b.lucro_apos_ads >= 0 ? 'pos' : 'neg'}`}>
                    {fmtPct(b.margem_apos_ads)}
                  </td>
                  <td className="num">{b.roas ? `${fmtNum(b.roas, 2)}×` : '—'}</td>
                </tr>
              ))}
              {!sort.sorted.length && (
                <tr>
                  <td colSpan={13} className="center-msg">
                    Sem movimento ainda. Registre vendas e Ads.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
