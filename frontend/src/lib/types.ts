export interface User {
  id: number
  name: string
  email: string
  role: 'owner' | 'member'
  organization_id: number
}

export interface Product {
  id: number
  sku: string
  nome: string
  variacao: string | null
  dropdown_name: string
  ativo: boolean
  estoque_atual: number
  valor_estoque: number
  custo_medio_atual: number
  // estoque explicado: entradas − vendas diretas − consumo em kits = estoque
  entradas: number
  vendas_diretas: number
  consumo_kits: number
}

export interface StockLot {
  id: number
  product_id: number
  produto: string
  lote_code: string | null
  data_entrada: string
  qty_in: number
  unit_cost: number
  custo_total: number
  consumed: number
  remaining: number
  valor_saldo: number
  status: string
}

export interface KitComponent {
  product_id: number
  produto?: string
  qty: number
}

export interface Kit {
  id: number
  sku: string
  nome: string
  ativo: boolean
  preco_referencia: number | null
  observacao: string | null
  components: KitComponent[]
  custo_atual: number
  qtd_itens: number
  estoque_possivel: number
}

export interface Channel {
  id: number
  name: string
  taxa_pct: number
  taxa_fixa: number
  taxa_afiliado_pct: number
  ativo: boolean
}

export interface Sale {
  id: number
  data_venda: string
  pedido: string | null
  item_type: 'product' | 'kit'
  channel_id: number | null
  channel: string | null
  sku: string
  nome: string
  qty: number
  preco_unitario: number
  receita_bruta: number
  taxa_shopee_pct: number
  taxa_shopee_rs: number
  taxa_afiliado_pct: number
  taxa_extra_rs: number
  taxa_fixa_rs: number
  outras_taxas: number
  receita_liquida: number
  cmv: number
  lucro: number
  margem: number
}

export interface AdSpend {
  id: number
  data: string
  canal: string | null
  valor: number
  observacao: string | null
}

export interface Settings {
  taxa_shopee_pct: number
  taxa_fixa: number
  taxa_afiliado_pct: number
}

export interface Dashboard {
  estoque_total: number
  valor_estoque: number
  receita_bruta: number
  taxas_totais: number
  receita_liquida: number
  cmv: number
  lucro_antes_ads: number
  ads_total: number
  lucro_apos_ads: number
  produtos: { dropdown_name: string; estoque: number; valor_estoque: number; custo_medio: number }[]
  kits: { nome: string; estoque_possivel: number }[]
}

export interface BalancoDia {
  data: string
  qty: number
  vendas: number
  receita_bruta: number
  taxa_shopee: number
  taxa_fixa: number
  taxa_afiliado: number
  outras_taxas: number
  receita_liquida: number
  cmv: number
  ads: number
  ads_por_venda: number
  lucro_apos_ads: number
  margem_apos_ads: number
  roas: number
}

export interface EstoqueDiaLinha {
  sku: string
  dropdown_name: string
  estoque_inicio: number
  venda_unitaria: number
  saida_via_kits: number
  total_saidas: number
  estoque_fim: number
  pct_estoque_inicial: number
}

export interface EstoqueDiario {
  data: string
  pecas_que_sairam: number
  estoque_final: number
  linhas: EstoqueDiaLinha[]
}

export interface EstoqueDiaResumo {
  data: string
  pecas_que_sairam: number
  estoque_final: number
}

export interface PricingResult {
  status: string
  erro: boolean
  preco_unitario: number
  receita_bruta?: number
  taxa_shopee_rs?: number
  taxa_afiliado_rs?: number
  taxa_fixa_rs?: number
  outros_custos?: number
  cmv?: number
  lucro?: number
  lucro_unitario?: number
  margem?: number
  preco_equilibrio?: number
  markup?: number
  item_nome?: string
  custo_unitario?: number
}
