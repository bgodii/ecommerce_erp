import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useImportAds, useImportOrders, useImportsStatus } from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtNum } from '../lib/format'

const STATUS_LABEL: Record<string, string> = {
  nao_pago: 'Não pago',
  a_enviar: 'A enviar',
  enviado: 'Enviado',
  entregue: 'Entregue',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
  devolucao: 'Devolução',
}

function UploadCard({
  title,
  desc,
  accept,
  mutation,
}: {
  title: string
  desc: string
  accept: string
  mutation: ReturnType<typeof useImportOrders> | ReturnType<typeof useImportAds>
}) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<any>(null)
  const [err, setErr] = useState('')
  const [done, setDone] = useState<any>(null)

  async function onFile(f: File | null) {
    setFile(f)
    setPreview(null)
    setDone(null)
    setErr('')
    if (!f) return
    try {
      setPreview(await mutation.mutateAsync({ file: f, dryRun: true }))
    } catch (e) {
      setErr(apiError(e, 'Não foi possível ler o arquivo'))
    }
  }

  async function confirm() {
    if (!file) return
    setErr('')
    try {
      setDone(await mutation.mutateAsync({ file, dryRun: false }))
      setPreview(null)
      setFile(null)
    } catch (e) {
      setErr(apiError(e))
    }
  }

  const s = preview?.summary
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="muted" style={{ marginTop: 0 }}>{desc}</p>
      {err && <div className="error">{err}</div>}
      {done && (
        <div className="status-line pos" style={{ marginBottom: 10 }}>
          ✓ Importado: {JSON.stringify(done.summary)
            .replace(/[{}"]/g, '')
            .replace(/,/g, ' · ')
            .replace(/:/g, ': ')}
        </div>
      )}
      <div className="field">
        <input type="file" accept={accept} onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
      </div>
      {mutation.isPending && !preview && <p className="muted">Lendo…</p>}
      {s && (
        <>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            {Object.entries(s).map(([k, v]) =>
              typeof v === 'object' ? null : (
                <span className="pill" key={k}>
                  {k.replace(/_/g, ' ')}: <b>{String(v)}</b>
                </span>
              ),
            )}
          </div>
          {s.por_status && (
            <div style={{ marginBottom: 10 }}>
              {Object.entries(s.por_status as Record<string, number>).map(([k, v]) => (
                <span className="pill" key={k}>
                  {STATUS_LABEL[k] ?? k}: {v}
                </span>
              ))}
            </div>
          )}
          <button className="btn" onClick={confirm} disabled={mutation.isPending}>
            {mutation.isPending ? 'Importando…' : 'Confirmar importação'}
          </button>
        </>
      )}
    </div>
  )
}

export default function Imports() {
  const { data: st } = useImportsStatus()
  const importOrders = useImportOrders()
  const importAds = useImportAds()

  return (
    <>
      <div className="page-title">Importar dados</div>
      <div className="page-sub">
        Suba os exports do marketplace. Reimportar o mesmo período só atualiza — nunca duplica.
      </div>

      {st && (
        <div className="grid kpis">
          <div className="card kpi">
            <div className="label">Pedidos importados</div>
            <div className="value">{fmtNum(st.pedidos_importados)}</div>
          </div>
          <div className="card kpi">
            <div className="label">Itens aguardando vínculo</div>
            <div className={`value ${st.itens_pendentes_vinculo ? 'neg' : 'pos'}`}>
              {fmtNum(st.itens_pendentes_vinculo)}
            </div>
          </div>
        </div>
      )}
      {!!st?.itens_pendentes_vinculo && (
        <div className="error" style={{ marginBottom: 14 }}>
          Há itens sem vínculo de SKU — eles não contam no estoque nem na receita até serem
          vinculados. <Link className="link" to="/vinculo-skus">Vincular agora →</Link>
        </div>
      )}

      <div className="grid cols-2">
        <UploadCard
          title="Pedidos (Order.all…xlsx)"
          desc="Shopee → Meus Pedidos → Exportar. Traz status, valores e as taxas reais por pedido."
          accept=".xlsx"
          mutation={importOrders}
        />
        <UploadCard
          title="ADS (relatórios .csv)"
          desc="Central de Anúncios → Exportar dados. Aceita os relatórios geral, palavra-chave, GMV MAX e grupo de anúncios."
          accept=".csv"
          mutation={importAds}
        />
      </div>

      {!!st?.ads_periodos?.length && (
        <>
          <h3 style={{ marginTop: 20 }}>Períodos de ADS importados</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Relatório</th>
                  <th>De</th>
                  <th>Até</th>
                  <th className="num">Linhas</th>
                  <th className="num">Investimento</th>
                </tr>
              </thead>
              <tbody>
                {st.ads_periodos.map((p: any, i: number) => (
                  <tr key={i}>
                    <td><span className="pill">{p.report_type}</span></td>
                    <td>{p.de}</td>
                    <td>{p.ate}</td>
                    <td className="num">{p.linhas}</td>
                    <td className="num">{fmtBRL(p.spend)}</td>
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
