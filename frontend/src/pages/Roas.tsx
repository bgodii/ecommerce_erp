import { FormEvent, useState } from 'react'
import { useChannels, useKits, useProducts, useSimulatePricing } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum, fmtPct } from '../lib/format'

export default function Roas() {
  const { data: products } = useProducts()
  const { data: kits } = useKits()
  const { data: channels } = useChannels()
  const sim = useSimulatePricing()

  const [form, setForm] = useState<any>({
    item: '',
    channel_id: '',
    preco: '',
    margem: '',
    ads: '',
    faturamento: '',
    vendas: '',
  })
  const set = (k: string) => (e: any) => setForm((f: any) => ({ ...f, [k]: e.target.value }))
  const [res, setRes] = useState<any>(null)
  const [err, setErr] = useState('')

  function itemCost(): number | null {
    const [t, id] = String(form.item).split(':')
    if (t === 'product') return products?.find((p) => p.id === Number(id))?.custo_medio_atual ?? null
    if (t === 'kit') return kits?.find((k) => k.id === Number(id))?.custo_atual ?? null
    return null
  }

  async function calcular(e: FormEvent) {
    e.preventDefault()
    setErr('')
    setRes(null)
    try {
      let margem = Number(form.margem) / 100
      const cost = itemCost()
      // Se escolheu item + preço, calcula a margem pelo backend (custo + taxas do e-commerce)
      if (cost != null && Number(form.preco) > 0) {
        const r = await sim.mutateAsync({
          custo_unitario: cost,
          qty: 1,
          modo: 'preco',
          channel_id: form.channel_id ? Number(form.channel_id) : null,
          preco_informado: Number(form.preco),
        })
        margem = r.margem ?? 0
        setForm((f: any) => ({ ...f, margem: String(+(margem * 100).toFixed(2)) }))
      }
      const ads = Number(form.ads)
      const fat = Number(form.faturamento)
      const vendas = Number(form.vendas)
      const roasAtual = ads > 0 ? fat / ads : 0
      const roasEquilibrio = margem > 0 ? 1 / margem : 0
      const lucroBruto = fat * margem
      const lucroAposAds = lucroBruto - ads
      const bom = margem > 0 && ads > 0 && roasAtual >= roasEquilibrio
      const custoPorVenda = vendas > 0 ? ads / vendas : 0
      setRes({ margem, roasAtual, roasEquilibrio, lucroBruto, lucroAposAds, bom, custoPorVenda })
    } catch (e) {
      setErr(apiError(e))
    }
  }

  return (
    <>
      <div className="page-title">Calculadora de ROAS</div>
      <div className="page-sub">
        Descubra o ROAS mínimo pra lucrar (= 1 ÷ margem) e avalie o seu ROAS do período
      </div>

      <div className="grid cols-2">
        <div className="card">
          {err && <div className="error">{err}</div>}
          <form onSubmit={calcular}>
            <h3>Margem do item (opcional)</h3>
            <div className="form-grid">
              <div className="field">
                <label>Produto ou kit</label>
                <select value={form.item} onChange={set('item')}>
                  <option value="">— não usar —</option>
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
              </div>
              <div className="field">
                <label>E-commerce</label>
                <select value={form.channel_id} onChange={set('channel_id')}>
                  <option value="">Automático</option>
                  {channels?.filter((c) => c.ativo).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Preço de venda (R$)</label>
                <input type="number" step="0.01" value={form.preco} onChange={set('preco')} />
              </div>
              <div className="field">
                <label>Margem líquida (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.margem}
                  onChange={set('margem')}
                  placeholder="ou calcule pelo item"
                />
              </div>
            </div>

            <h3 style={{ marginTop: 6 }}>Seu período (dados da Shopee)</h3>
            <div className="form-grid">
              <div className="field">
                <label>Investimento em Ads (R$)</label>
                <input type="number" step="0.01" value={form.ads} onChange={set('ads')} required />
              </div>
              <div className="field">
                <label>Faturamento (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.faturamento}
                  onChange={set('faturamento')}
                  required
                />
              </div>
              <div className="field">
                <label>Nº de vendas (opcional)</label>
                <input type="number" value={form.vendas} onChange={set('vendas')} />
              </div>
            </div>
            <button className="btn" disabled={sim.isPending}>
              {sim.isPending ? 'Calculando…' : 'Calcular'}
            </button>
          </form>
        </div>

        <div className="card">
          <h3>Resultado</h3>
          {!res ? (
            <p className="muted">Preencha e clique em Calcular.</p>
          ) : (
            <>
              <div className="card kpi" style={{ marginBottom: 14 }}>
                <div className="label">Veredito</div>
                <div className={`value ${res.bom ? 'pos' : 'neg'}`}>
                  {res.margem <= 0
                    ? 'Informe a margem'
                    : res.bom
                      ? '✅ ROAS bom — lucrando'
                      : '⚠️ ROAS ruim — no prejuízo'}
                </div>
              </div>
              <table>
                <tbody>
                  <Row label="Margem líquida (antes de Ads)" value={fmtPct(res.margem)} />
                  <Row
                    label="ROAS de equilíbrio (mínimo)"
                    value={res.roasEquilibrio ? `${fmtNum(res.roasEquilibrio, 2)}×` : '—'}
                    strong
                  />
                  <Row
                    label="Seu ROAS atual"
                    value={res.roasAtual ? `${fmtNum(res.roasAtual, 2)}×` : '—'}
                    strong
                    pos={res.bom}
                  />
                  <Row label="Lucro bruto (antes de Ads)" value={fmtBRL(res.lucroBruto)} />
                  <Row
                    label="Lucro após Ads"
                    value={fmtBRL(res.lucroAposAds)}
                    pos={res.lucroAposAds >= 0}
                    strong
                  />
                  {res.custoPorVenda > 0 && (
                    <Row label="Custo de Ads por venda" value={fmtBRL(res.custoPorVenda)} />
                  )}
                </tbody>
              </table>
              <p className="status-line" style={{ marginTop: 12 }}>
                Regra: seu ROAS precisa ficar <b>acima do ROAS de equilíbrio</b> (= 1 ÷ margem) pra
                lucrar com os anúncios.
              </p>
            </>
          )}
        </div>
      </div>
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
