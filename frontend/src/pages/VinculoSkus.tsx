import { useState } from 'react'
import {
  useCreateMapping,
  useDeleteMapping,
  useKits,
  useMappings,
  usePendingMappings,
  useProducts,
  useSaveProduct,
} from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtNum } from '../lib/format'

export default function VinculoSkus() {
  const { data: pendentes, isLoading } = usePendingMappings()
  const { data: vinculos } = useMappings()
  const { data: products } = useProducts()
  const { data: kits } = useKits()
  const createMapping = useCreateMapping()
  const deleteMapping = useDeleteMapping()
  const saveProduct = useSaveProduct()

  const [sel, setSel] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  async function vincular(matchKey: string, value: string) {
    setErr('')
    setMsg('')
    const [tipo, idStr] = value.split(':')
    try {
      const r = await createMapping.mutateAsync({
        match_key: matchKey,
        product_id: tipo === 'product' ? Number(idStr) : null,
        kit_id: tipo === 'kit' ? Number(idStr) : null,
      })
      setMsg(`Vinculado — ${r.itens_aplicados} item(ns) atualizados.`)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  async function criarProduto(g: any) {
    setErr('')
    const nomeBase = g.variation_name || g.sku_var || g.product_name || 'Novo produto'
    const nome = window.prompt('Nome do novo produto:', nomeBase)
    if (!nome) return
    const sku = window.prompt('SKU do novo produto:', (g.sku_var || nome).toLowerCase().replace(/\s+/g, '-'))
    if (!sku) return
    try {
      const p = await saveProduct.mutateAsync({ sku, nome, dropdown_name: nome })
      await vincular(g.match_key, `product:${p.id}`)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  return (
    <>
      <div className="page-title">Vínculo de SKUs</div>
      <div className="page-sub">
        Ligue cada variação do marketplace a um produto ou kit do seu catálogo. Itens sem vínculo
        não contam no estoque nem na receita.
      </div>

      {msg && <div className="status-line pos" style={{ marginBottom: 10 }}>{msg}</div>}
      {err && <div className="error">{err}</div>}

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : !pendentes?.length ? (
        <div className="card" style={{ marginBottom: 18 }}>
          ✅ Nenhuma pendência — todos os itens importados estão vinculados.
        </div>
      ) : (
        <div className="table-wrap" style={{ marginBottom: 18 }}>
          <table>
            <thead>
              <tr>
                <th>Item do marketplace</th>
                <th className="num">Unidades</th>
                <th>Sugestão</th>
                <th style={{ minWidth: 260 }}>Vincular a</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pendentes.map((g: any) => {
                const best = g.sugestoes?.[0]
                return (
                  <tr key={g.match_key}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{g.sku_var || g.variation_name}</div>
                      <div className="muted" style={{ whiteSpace: 'normal', maxWidth: 320 }}>
                        {g.product_name}
                      </div>
                    </td>
                    <td className="num">{fmtNum(g.qtd_unidades)}</td>
                    <td>
                      {best && best.score > 0.3 ? (
                        <button
                          className="btn secondary sm"
                          onClick={() => vincular(g.match_key, `${best.tipo}:${best.id}`)}
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
                          value={sel[g.match_key] ?? ''}
                          onChange={(e) => setSel((s) => ({ ...s, [g.match_key]: e.target.value }))}
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
                          disabled={!sel[g.match_key] || createMapping.isPending}
                          onClick={() => vincular(g.match_key, sel[g.match_key])}
                        >
                          Vincular
                        </button>
                      </div>
                    </td>
                    <td>
                      <button className="btn ghost sm" onClick={() => criarProduto(g)}>
                        + Criar produto
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!!vinculos?.length && (
        <>
          <h3>Vínculos existentes</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Chave do marketplace</th>
                  <th>Destino no ERP</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {vinculos.map((m: any) => (
                  <tr key={m.id}>
                    <td style={{ whiteSpace: 'normal' }}>{m.match_key}</td>
                    <td>
                      <span className="pill">{m.tipo === 'kit' ? '🧩 ' : '👕 '}{m.destino}</span>
                    </td>
                    <td>
                      <button
                        className="btn ghost sm neg"
                        onClick={() => {
                          if (confirm('Desfazer este vínculo? Os itens voltam a ficar pendentes.'))
                            deleteMapping.mutate(m.id)
                        }}
                      >
                        Desfazer
                      </button>
                    </td>
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
