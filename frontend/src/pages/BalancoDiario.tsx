import { SortTh, useSort } from '../components/Sortable'
import Th from '../components/Th'
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
                <SortTh<BalancoDia> label="Data" k="data" sort={sort} help="Dia da venda" />
                <Th label="Qtd" help="Unidades vendidas no dia" num />
                <Th label="Receita" help="Total pago pelos clientes no dia" num />
                <Th label="Comissão" help="Comissão percentual cobrada pelo marketplace" num />
                <Th label="Taxa fixa" help="Taxa fixa por pedido" num />
                <Th label="Afiliado/Extra" help="Comissão de afiliado ou taxa extra da campanha" num />
                <Th label="Outras" help="Outras deduções (cupons, ajustes, taxa de transação)" num />
                <Th label="Líquida" help="Receita menos todas as taxas — antes do custo do produto" num />
                <Th label="CMV" help="Custo das mercadorias vendidas no dia (FIFO)" num />
                <Th label="Ads" help="Investimento em anúncios no dia" num />
                <Th label="Ads/venda" help="Quanto de anúncio custou cada venda (ads ÷ nº de vendas)" num />
                <Th label="Lucro após Ads" help="Líquida − CMV − Ads. O que realmente sobrou no dia." num />
                <Th label="Margem" help="Lucro após Ads ÷ receita" num />
                <Th label="ROAS" help="Retorno dos anúncios: receita ÷ investimento em ads" num />
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
                  <td className="num">{fmtBRL(b.ads_por_venda)}</td>
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
                  <td colSpan={14} className="center-msg">
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
