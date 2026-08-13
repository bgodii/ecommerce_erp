import { useEffect, useState } from 'react'
import { SortTh, useSort } from '../components/Sortable'
import { useEstoqueDiario, useEstoqueDiarioRange } from '../hooks/queries'
import { fmtDate, fmtNum, fmtPct, todayISO } from '../lib/format'
import type { EstoqueDiaResumo } from '../lib/types'

const daysAgoISO = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

export default function EstoqueDiario() {
  // Abre já com os últimos 7 dias aplicados
  const [from, setFrom] = useState(daysAgoISO(6))
  const [to, setTo] = useState(todayISO())
  const { data: resumo, isLoading } = useEstoqueDiarioRange(from, to)
  const sort = useSort<EstoqueDiaResumo>(resumo, 'data', 'desc')

  const [day, setDay] = useState('')
  // Detalhe padrão = dia mais recente com movimento
  useEffect(() => {
    if (resumo && resumo.length) {
      const exists = resumo.some((r) => r.data === day)
      if (!day || !exists) setDay(resumo[resumo.length - 1].data)
    }
  }, [resumo]) // eslint-disable-line react-hooks/exhaustive-deps

  const { data: detalhe } = useEstoqueDiario(day)

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Estoque Diário</div>
          <div className="page-sub">Peças que saíram por dia (kits explodidos em componentes)</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className="btn secondary sm"
              onClick={() => {
                setFrom(daysAgoISO(6))
                setTo(todayISO())
              }}
            >
              7 dias
            </button>
            <button
              className="btn secondary sm"
              onClick={() => {
                setFrom(daysAgoISO(29))
                setTo(todayISO())
              }}
            >
              30 dias
            </button>
            <button
              className="btn secondary sm"
              onClick={() => {
                setFrom('')
                setTo('')
              }}
            >
              Tudo
            </button>
          </div>
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

      <h3>Todos os dias</h3>
      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh<EstoqueDiaResumo> label="Data" k="data" sort={sort} />
                <SortTh<EstoqueDiaResumo> label="Peças que saíram" k="pecas_que_sairam" sort={sort} num />
                <SortTh<EstoqueDiaResumo> label="Estoque final" k="estoque_final" sort={sort} num />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((r) => (
                <tr key={r.data} className={r.data === day ? 'row-selected' : ''}>
                  <td>{fmtDate(r.data)}</td>
                  <td className="num">{fmtNum(r.pecas_que_sairam)}</td>
                  <td className="num">{fmtNum(r.estoque_final)}</td>
                  <td>
                    <button className="btn ghost sm" onClick={() => setDay(r.data)}>
                      Ver detalhe
                    </button>
                  </td>
                </tr>
              ))}
              {!sort.sorted.length && (
                <tr>
                  <td colSpan={4} className="center-msg">
                    Sem movimento de vendas no período.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {day && detalhe && (
        <>
          <h3 style={{ marginTop: 22 }}>Detalhe do dia {fmtDate(day)}</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Produto</th>
                  <th className="num">Início do dia</th>
                  <th className="num">Venda unitária</th>
                  <th className="num">Saída via kits</th>
                  <th className="num">Total saídas</th>
                  <th className="num">Fim do dia</th>
                  <th className="num">% do inicial</th>
                </tr>
              </thead>
              <tbody>
                {detalhe.linhas.map((l) => (
                  <tr key={l.sku}>
                    <td>{l.sku}</td>
                    <td>{l.dropdown_name}</td>
                    <td className="num">{fmtNum(l.estoque_inicio)}</td>
                    <td className="num">{fmtNum(l.venda_unitaria)}</td>
                    <td className="num">{fmtNum(l.saida_via_kits)}</td>
                    <td className="num">{fmtNum(l.total_saidas)}</td>
                    <td className="num">{fmtNum(l.estoque_fim)}</td>
                    <td className="num">{fmtPct(l.pct_estoque_inicial)}</td>
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
