import { useState } from 'react'
import { Link } from 'react-router-dom'
import Th from '../components/Th'
import { useKits, useLinkListing, useListings, useProducts } from '../hooks/queries'
import { apiError } from '../lib/api'

/** Liga cada anúncio do marketplace a um produto/kit para a Análise de ADS usar a
 *  margem REAL daquele item (ROAS even e CPC máximo por anúncio). */
export default function VinculoAnuncios() {
  const { data: listings, isLoading } = useListings()
  const { data: products } = useProducts()
  const { data: kits } = useKits()
  const link = useLinkListing()
  const [sel, setSel] = useState<Record<number, string>>({})
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  async function vincular(id: number, value: string) {
    setErr('')
    setMsg('')
    const [tipo, idStr] = value.split(':')
    try {
      await link.mutateAsync({
        id,
        product_id: tipo === 'product' ? Number(idStr) : null,
        kit_id: tipo === 'kit' ? Number(idStr) : null,
      })
      setMsg('Anúncio vinculado — a Análise de ADS já usa a margem desse item.')
    } catch (e) {
      setErr(apiError(e))
    }
  }

  const semVinculo = (listings ?? []).filter((l: any) => !l.vinculado_a).length

  return (
    <>
      <div className="page-title">Vincular anúncios</div>
      <div className="page-sub">
        Ligue cada anúncio ao produto/kit correspondente. Assim o <b>ROAS even</b> e o{' '}
        <b>CPC máximo</b> passam a usar a margem real daquele item, em vez da média da loja.
      </div>

      {msg && <div className="status-line pos">{msg}</div>}
      {err && <div className="error">{err}</div>}
      {!!semVinculo && (
        <div className="insight info" style={{ marginBottom: 14 }}>
          <span className="ic">ℹ️</span>
          <div>
            <b>{semVinculo} anúncio(s) sem vínculo</b>
            <p>Enquanto não vincular, eles usam a margem média da loja no cálculo.</p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : !listings?.length ? (
        <div className="card">
          Nenhum anúncio ainda — <Link className="link" to="/importar">importe um relatório de ADS</Link>.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <Th label="Anúncio" help="Nome do anúncio no marketplace" />
                <Th label="ID" help="ID do produto no marketplace (vem do relatório de ADS)" />
                <Th label="Vinculado a" help="Produto ou kit do seu catálogo usado para calcular a margem" />
                <Th label="Sugestão" help="Melhor palpite por similaridade de nome" />
                <Th label="Vincular a" help="Escolha manualmente o produto ou kit" />
              </tr>
            </thead>
            <tbody>
              {listings.map((l: any) => {
                const best = l.sugestoes?.[0]
                return (
                  <tr key={l.id}>
                    <td style={{ whiteSpace: 'normal', maxWidth: 340 }}>{l.nome}</td>
                    <td className="muted">{l.listing_id}</td>
                    <td>
                      {l.vinculado_a ? (
                        <span className="verdict ok">{l.vinculado_a}</span>
                      ) : (
                        <span className="verdict atencao">margem da loja</span>
                      )}
                    </td>
                    <td>
                      {best && best.score > 0.3 && !l.vinculado_a ? (
                        <button
                          className="btn secondary sm"
                          onClick={() => vincular(l.id, `${best.tipo}:${best.id}`)}
                        >
                          {best.nome} ({Math.round(best.score * 100)}%)
                        </button>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <select
                          value={sel[l.id] ?? ''}
                          onChange={(e) => setSel((s) => ({ ...s, [l.id]: e.target.value }))}
                        >
                          <option value="">Escolher…</option>
                          {products?.length && (
                            <optgroup label="Produtos">
                              {products.map((p) => (
                                <option key={'p' + p.id} value={`product:${p.id}`}>
                                  {p.dropdown_name}
                                </option>
                              ))}
                            </optgroup>
                          )}
                          {kits?.length && (
                            <optgroup label="Kits">
                              {kits.map((k) => (
                                <option key={'k' + k.id} value={`kit:${k.id}`}>
                                  {k.nome}
                                </option>
                              ))}
                            </optgroup>
                          )}
                        </select>
                        <button
                          className="btn sm"
                          disabled={!sel[l.id] || link.isPending}
                          onClick={() => vincular(l.id, sel[l.id])}
                        >
                          Vincular
                        </button>
                        {l.vinculado_a && (
                          <button
                            className="btn ghost sm neg"
                            onClick={() => link.mutate({ id: l.id, product_id: null, kit_id: null })}
                          >
                            Desfazer
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
