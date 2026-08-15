import { AxiosError } from 'axios'
import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import Modal from '../components/Modal'
import { SortTh, useSort } from '../components/Sortable'
import Th from '../components/Th'
import {
  useChannels,
  useDeleteSale,
  useDuplicatedSales,
  useImportSales,
  useRemoveDuplicatedSales,
  useKits,
  useProducts,
  useSales,
  useSaveSale,
} from '../hooks/queries'
import { apiError } from '../lib/api'
import { fmtBRL, fmtDate, fmtNum, fmtPct, todayISO } from '../lib/format'
import type { Sale } from '../lib/types'

export default function Vendas() {
  const { data: sales, isLoading } = useSales()
  const sort = useSort<Sale>(sales, 'data_venda', 'desc')
  const { data: products } = useProducts()
  const { data: kits } = useKits()
  const { data: channels } = useChannels()
  const save = useSaveSale()
  const del = useDeleteSale()
  const importSales = useImportSales()
  const { data: dups } = useDuplicatedSales()
  const removeDups = useRemoveDuplicatedSales()
  const [open, setOpen] = useState(false)
  const [err, setErr] = useState('')
  // Import CSV (ERP-030)
  const [importOpen, setImportOpen] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<any>(null)
  const [importErr, setImportErr] = useState('')
  const [form, setForm] = useState<any>({
    data_venda: todayISO(),
    pedido: '',
    item: '',
    channel_id: '',
    qty: 1,
    preco_unitario: 0,
    taxa_afiliado_pct: 0,
    outras_taxas: 0,
  })
  const set = (k: string) => (e: any) => setForm((f: any) => ({ ...f, [k]: e.target.value }))

  function openNew() {
    setErr('')
    setForm({
      data_venda: todayISO(),
      pedido: '',
      item: '',
      channel_id: channels?.find((c) => c.ativo)?.id ?? '',
      qty: 1,
      preco_unitario: 0,
      taxa_afiliado_pct: 0,
      outras_taxas: 0,
    })
    setOpen(true)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setErr('')
    const [item_type, idStr] = String(form.item).split(':')
    if (!item_type || !idStr) {
      setErr('Selecione um produto ou kit')
      return
    }
    const payload = {
      data_venda: form.data_venda,
      pedido: form.pedido || null,
      item_type,
      product_id: item_type === 'product' ? Number(idStr) : null,
      kit_id: item_type === 'kit' ? Number(idStr) : null,
      channel_id: form.channel_id ? Number(form.channel_id) : null,
      qty: Number(form.qty),
      preco_unitario: Number(form.preco_unitario),
      taxa_afiliado_pct: Number(form.taxa_afiliado_pct) / 100,
      outras_taxas: Number(form.outras_taxas),
    }
    try {
      await save.mutateAsync(payload)
      setOpen(false)
    } catch (e) {
      // Guardrail de estoque (ERP-002): 409 → confirmar e lançar mesmo assim
      if ((e as AxiosError).response?.status === 409) {
        if (window.confirm(`${apiError(e)}\n\nDeseja lançar mesmo assim?`)) {
          try {
            await save.mutateAsync({ ...payload, permitir_sem_estoque: true })
            setOpen(false)
          } catch (e2) {
            setErr(apiError(e2))
          }
        }
        return
      }
      setErr(apiError(e))
    }
  }

  async function remove(id: number) {
    if (!confirm('Excluir esta venda?')) return
    try {
      await del.mutateAsync(id)
    } catch (e) {
      alert(apiError(e))
    }
  }

  function openImport() {
    setImportFile(null)
    setPreview(null)
    setImportErr('')
    setImportOpen(true)
  }

  async function onFile(f: File | null) {
    setImportFile(f)
    setPreview(null)
    setImportErr('')
    if (!f) return
    try {
      setPreview(await importSales.mutateAsync({ file: f, dryRun: true }))
    } catch (e) {
      setImportErr(apiError(e, 'Não foi possível ler o arquivo'))
    }
  }

  async function doImport() {
    if (!importFile) return
    try {
      await importSales.mutateAsync({ file: importFile, dryRun: false })
      setImportOpen(false)
    } catch (e) {
      setImportErr(apiError(e))
    }
  }

  function downloadTemplate() {
    const csv =
      'data;pedido;sku;qty;preco_unitario;taxa_afiliado_pct;outras_taxas\n' +
      '2026-08-12;PEDIDO123;blusa-azul;1;22,99;;\n'
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'modelo-vendas.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportCSV() {
    const rows = sort.sorted
    if (!rows.length) return
    const br = (n: number) => String(n ?? 0).replace('.', ',')
    const header = [
      'Data', 'Pedido', 'Item', 'SKU', 'Qtd', 'Preço Unit.', 'Receita Bruta',
      'Taxas', 'Receita Líquida', 'CMV', 'Lucro', 'Margem %',
    ]
    const q = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const lines = rows.map((s) => {
      const taxas = s.taxa_shopee_rs + s.taxa_fixa_rs + s.taxa_extra_rs + s.outras_taxas
      return [
        s.data_venda, s.pedido ?? '', s.nome, s.sku, s.qty, br(s.preco_unitario),
        br(s.receita_bruta), br(taxas), br(s.receita_liquida), br(s.cmv), br(s.lucro),
        br(s.margem * 100),
      ]
        .map(q)
        .join(';')
    })
    const csv = ['﻿' + header.map(q).join(';'), ...lines].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `vendas-${todayISO()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const hasItems = !!products?.length || !!kits?.length
  const semCusto = (sales ?? []).filter((s) => s.cmv <= 0).length

  return (
    <>
      <div className="toolbar">
        <div>
          <div className="page-title">Vendas</div>
          <div className="page-sub">
            Pedidos importados usam as <b>taxas reais</b> do marketplace; CMV via FIFO e lucro são
            calculados automaticamente.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn secondary" onClick={exportCSV} disabled={!sales?.length}>
            Exportar CSV
          </button>
          <button className="btn secondary" onClick={openImport} disabled={!hasItems}>
            Importar CSV
          </button>
          <button className="btn" onClick={openNew} disabled={!hasItems}>
            + Nova venda
          </button>
        </div>
      </div>

      {!!dups?.total && (
        <div className="insight alerta" style={{ marginBottom: 14 }}>
          <span className="ic">🔁</span>
          <div style={{ flex: 1 }}>
            <b>{dups.total} venda(s) lançada(s) à mão que também vieram do import</b>
            <p>
              Pedidos: {dups.vendas.slice(0, 5).map((v: any) => v.pedido).join(', ')}
              {dups.total > 5 ? '…' : ''}. Elas <b>não</b> estão sendo somadas em dobro (o pedido
              importado tem prioridade), mas continuam guardadas. Pode remover com segurança.
            </p>
            <button
              className="btn sm"
              style={{ marginTop: 8 }}
              disabled={removeDups.isPending}
              onClick={() => {
                if (confirm(`Remover ${dups.total} lançamento(s) manual(is) duplicado(s)?`))
                  removeDups.mutate()
              }}
            >
              {removeDups.isPending ? 'Removendo…' : `Remover ${dups.total} duplicada(s)`}
            </button>
          </div>
        </div>
      )}

      {semCusto > 0 && (
        <div className="insight alerta" style={{ marginBottom: 14 }}>
          <span className="ic">⚠️</span>
          <div>
            <b>{semCusto} venda(s) sem custo de compra cadastrado</b>
            <p>
              O lucro e a margem dessas linhas (marcadas com <b>*</b>) estão superestimados porque o
              CMV está zerado. Registre o estoque e o preço pago em{' '}
              <Link className="link" to="/entradas">Entradas</Link>.
            </p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="center-msg">Carregando…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh<Sale> label="Data" k="data_venda" sort={sort} help="Data em que a venda foi feita" />
                <Th label="Pedido" help="Número do pedido no marketplace" />
                <Th label="Item" help="Produto ou kit vendido" />
                <Th label="Canal" help="E-commerce onde a venda aconteceu (Shopee, TikTok…)" />
                <Th label="Origem" help="Importado = veio da planilha de pedidos (com status real). Manual = lançado por você." />
                <Th label="Qtd" help="Unidades vendidas nesta linha" num />
                <Th label="Preço" help="Preço unitário cobrado do cliente" num />
                <Th label="Receita" help="Quanto o cliente pagou pelos produtos (qtd × preço)" num />
                <Th label="Taxas" help="Tudo que o marketplace cobrou: comissão + serviço + transação + afiliado" num />
                <Th label="Após taxas" help="Receita menos as taxas do marketplace — ainda NÃO desconta o custo do produto" num />
                <Th label="Custo (CMV)" help="Quanto você pagou pelo produto (custo da mercadoria vendida, por FIFO). Vem das Entradas de estoque." num />
                <Th label="Lucro real" help="Após taxas − custo do produto. É o que realmente sobra da venda (antes de anúncios)." num />
                <Th label="Margem real" help="Lucro real ÷ receita. Quanto de cada R$ 100 vendidos vira lucro." num />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sort.sorted.map((s) => {
                const taxas = s.taxa_shopee_rs + s.taxa_fixa_rs + s.taxa_extra_rs + s.outras_taxas
                return (
                  <tr key={s.id}>
                    <td>{fmtDate(s.data_venda)}</td>
                    <td>{s.pedido}</td>
                    <td>{s.nome}</td>
                    <td>{s.channel ?? '—'}</td>
                    <td>
                      {s.origem === 'importado' ? (
                        <span className="pill" title={`Pedido importado · status: ${s.status ?? '—'}`}>
                          📥 {s.status ?? 'importado'}
                        </span>
                      ) : (
                        <span className="pill">✍️ manual</span>
                      )}
                    </td>
                    <td className="num">{fmtNum(s.qty)}</td>
                    <td className="num">{fmtBRL(s.preco_unitario)}</td>
                    <td className="num">{fmtBRL(s.receita_bruta)}</td>
                    <td className="num">{fmtBRL(taxas)}</td>
                    <td className="num">{fmtBRL(s.receita_liquida)}</td>
                    <td className="num">
                      {s.cmv > 0 ? (
                        fmtBRL(s.cmv)
                      ) : (
                        <span
                          className="verdict atencao"
                          title="Custo de compra não cadastrado — registre uma entrada de estoque para este produto"
                        >
                          sem custo
                        </span>
                      )}
                    </td>
                    <td className={`num ${s.lucro >= 0 ? 'pos' : 'neg'}`} title={s.cmv > 0 ? '' : 'Superestimado: falta o custo de compra'}>
                      {fmtBRL(s.lucro)}{s.cmv > 0 ? '' : ' *'}
                    </td>
                    <td className={`num ${s.lucro >= 0 ? 'pos' : 'neg'}`}>
                      {fmtPct(s.margem)}{s.cmv > 0 ? '' : ' *'}
                    </td>
                    <td>
                      {s.origem === 'importado' ? (
                        <span className="muted" style={{ fontSize: 12 }} title="Vem do pedido importado — altere no marketplace e reimporte">
                          —
                        </span>
                      ) : (
                        <button className="btn ghost sm neg" onClick={() => remove(s.id)}>
                          Excluir
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {!sort.sorted.length && (
                <tr>
                  <td colSpan={14} className="center-msg">
                    Nenhuma venda ainda. Importe os pedidos do marketplace ou lance manualmente.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {open && (
        <Modal title="Nova venda" onClose={() => setOpen(false)}>
          {err && <div className="error">{err}</div>}
          <form onSubmit={submit}>
            <div className="field">
              <label>Produto ou kit</label>
              <select value={form.item} onChange={set('item')} required>
                <option value="">Selecione…</option>
                {products?.length && (
                  <optgroup label="Produtos">
                    {products.map((p) => (
                      <option key={`p${p.id}`} value={`product:${p.id}`}>
                        {p.dropdown_name}
                      </option>
                    ))}
                  </optgroup>
                )}
                {kits?.length && (
                  <optgroup label="Kits">
                    {kits.map((k) => (
                      <option key={`k${k.id}`} value={`kit:${k.id}`}>
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
                <option value="">Padrão da loja</option>
                {channels
                  ?.filter((c) => c.ativo)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>
            <div className="form-grid">
              <div className="field">
                <label>Data da venda</label>
                <input type="date" value={form.data_venda} onChange={set('data_venda')} required />
              </div>
              <div className="field">
                <label>Nº do pedido (opcional)</label>
                <input value={form.pedido} onChange={set('pedido')} />
              </div>
              <div className="field">
                <label>Quantidade</label>
                <input type="number" min={1} value={form.qty} onChange={set('qty')} required />
              </div>
              <div className="field">
                <label>Preço unitário (R$)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.preco_unitario}
                  onChange={set('preco_unitario')}
                  required
                />
              </div>
              <div className="field">
                <label>Taxa afiliado / extra (%)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.taxa_afiliado_pct}
                  onChange={set('taxa_afiliado_pct')}
                />
              </div>
              <div className="field">
                <label>Outras taxas (R$)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.outras_taxas}
                  onChange={set('outras_taxas')}
                />
              </div>
            </div>
            <p className="status-line">
              As taxas vêm do e-commerce selecionado.
            </p>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setOpen(false)}>
                Cancelar
              </button>
              <button className="btn" disabled={save.isPending}>
                {save.isPending ? 'Salvando…' : 'Registrar venda'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {importOpen && (
        <Modal title="Importar vendas (CSV)" onClose={() => setImportOpen(false)}>
          {importErr && <div className="error">{importErr}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            Colunas: <code>data, pedido, sku, qty, preco_unitario</code> (taxas opcionais). Aceita
            separador <code>,</code> ou <code>;</code> e vírgula decimal.{' '}
            <span className="link" onClick={downloadTemplate}>
              Baixar modelo
            </span>
          </p>
          <div className="field">
            <label>Arquivo CSV</label>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {importSales.isPending && !preview && <p className="muted">Lendo arquivo…</p>}

          {preview && (
            <>
              <div className="grid kpis">
                <div className="card kpi">
                  <div className="label">Novos</div>
                  <div className="value pos">{preview.summary.novos}</div>
                </div>
                <div className="card kpi">
                  <div className="label">Duplicados</div>
                  <div className="value">{preview.summary.duplicados}</div>
                </div>
                <div className="card kpi">
                  <div className="label">Erros</div>
                  <div className="value neg">{preview.summary.erros}</div>
                </div>
                <div className="card kpi">
                  <div className="label">Total</div>
                  <div className="value">{preview.summary.total}</div>
                </div>
              </div>

              {preview.errors?.length > 0 && (
                <div className="error" style={{ marginTop: 10 }}>
                  {preview.errors.slice(0, 5).map((er: any, i: number) => (
                    <div key={i}>
                      Linha {er.linha ?? '—'}: {er.erro}
                    </div>
                  ))}
                </div>
              )}

              {preview.preview?.length > 0 && (
                <div
                  className="table-wrap"
                  style={{ marginTop: 10, maxHeight: 220, overflowY: 'auto' }}
                >
                  <table>
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Pedido</th>
                        <th>Item</th>
                        <th className="num">Qtd</th>
                        <th className="num">Preço</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.preview.slice(0, 20).map((r: any, i: number) => (
                        <tr key={i}>
                          <td>{fmtDate(r.data_venda)}</td>
                          <td>{r.pedido}</td>
                          <td>{r.item ?? r.sku}</td>
                          <td className="num">{r.qty}</td>
                          <td className="num">{fmtBRL(r.preco_unitario)}</td>
                          <td>
                            <span className="pill">{r.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          <div className="modal-actions">
            <button type="button" className="btn secondary" onClick={() => setImportOpen(false)}>
              Cancelar
            </button>
            <button
              className="btn"
              disabled={!preview || preview.summary.novos === 0 || importSales.isPending}
              onClick={doImport}
            >
              {importSales.isPending ? 'Importando…' : `Importar ${preview?.summary.novos ?? 0} venda(s)`}
            </button>
          </div>
        </Modal>
      )}
    </>
  )
}
