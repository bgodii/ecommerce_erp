import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type {
  AdSpend,
  BalancoDia,
  Channel,
  Dashboard,
  EstoqueDiaResumo,
  EstoqueDiario,
  Kit,
  PricingResult,
  Product,
  Sale,
  StockLot,
  User,
} from '../lib/types'

// Muitos números são derivados (estoque, FIFO, dashboard...). Após qualquer alteração,
// invalidamos todas as chaves que dependem do estado do domínio.
const DOMAIN_KEYS = [
  'dashboard',
  'products',
  'lots',
  'kits',
  'sales',
  'balanco',
  'estoque-diario',
  'estoque-diario-range',
]

function useDomainInvalidation() {
  const qc = useQueryClient()
  return () => DOMAIN_KEYS.forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
}

// ---- Relatórios ----
export const useDashboard = () =>
  useQuery({ queryKey: ['dashboard'], queryFn: async () => (await api.get<Dashboard>('/reports/dashboard')).data })

export const useBalanco = (from?: string, to?: string) =>
  useQuery({
    queryKey: ['balanco', from, to],
    queryFn: async () =>
      (await api.get<BalancoDia[]>('/reports/balanco-diario', { params: { from, to } })).data,
  })

export const useEstoqueDiario = (data: string) =>
  useQuery({
    queryKey: ['estoque-diario', data],
    queryFn: async () =>
      (await api.get<EstoqueDiario>('/reports/estoque-diario', { params: { data } })).data,
    enabled: !!data,
  })

export const useEstoqueDiarioRange = (from?: string, to?: string) =>
  useQuery({
    queryKey: ['estoque-diario-range', from, to],
    queryFn: async () =>
      (await api.get<EstoqueDiaResumo[]>('/reports/estoque-diario-range', { params: { from, to } }))
        .data,
  })

// ---- Produtos ----
export const useProducts = () =>
  useQuery({ queryKey: ['products'], queryFn: async () => (await api.get<Product[]>('/products')).data })

export function useSaveProduct() {
  const invalidate = useDomainInvalidation()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/products/${id}`, body)).data : (await api.post('/products', body)).data,
    onSuccess: invalidate,
  })
}

export function useDeleteProduct() {
  const invalidate = useDomainInvalidation()
  return useMutation({ mutationFn: async (id: number) => api.delete(`/products/${id}`), onSuccess: invalidate })
}

// ---- Entradas (lotes) ----
export const useLots = () =>
  useQuery({ queryKey: ['lots'], queryFn: async () => (await api.get<StockLot[]>('/stock-lots')).data })

export function useSaveLot() {
  const invalidate = useDomainInvalidation()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/stock-lots/${id}`, body)).data : (await api.post('/stock-lots', body)).data,
    onSuccess: invalidate,
  })
}

export function useDeleteLot() {
  const invalidate = useDomainInvalidation()
  return useMutation({ mutationFn: async (id: number) => api.delete(`/stock-lots/${id}`), onSuccess: invalidate })
}

// ---- Kits ----
export const useKits = () =>
  useQuery({ queryKey: ['kits'], queryFn: async () => (await api.get<Kit[]>('/kits')).data })

export function useSaveKit() {
  const invalidate = useDomainInvalidation()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/kits/${id}`, body)).data : (await api.post('/kits', body)).data,
    onSuccess: invalidate,
  })
}

export function useDeleteKit() {
  const invalidate = useDomainInvalidation()
  return useMutation({ mutationFn: async (id: number) => api.delete(`/kits/${id}`), onSuccess: invalidate })
}

// ---- Vendas ----
export const useSales = () =>
  useQuery({ queryKey: ['sales'], queryFn: async () => (await api.get<Sale[]>('/sales')).data })

export function useSaveSale() {
  const invalidate = useDomainInvalidation()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/sales/${id}`, body)).data : (await api.post('/sales', body)).data,
    onSuccess: invalidate,
  })
}

export function useDeleteSale() {
  const invalidate = useDomainInvalidation()
  return useMutation({ mutationFn: async (id: number) => api.delete(`/sales/${id}`), onSuccess: invalidate })
}

export function useImportSales() {
  const invalidate = useDomainInvalidation()
  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const fd = new FormData()
      fd.append('file', file)
      return (await api.post('/sales/import', fd, { params: { dry_run: dryRun } })).data
    },
    onSuccess: (_data, vars) => {
      if (!vars.dryRun) invalidate()
    },
  })
}

// ---- Ads ----
export const useAds = () =>
  useQuery({ queryKey: ['ads'], queryFn: async () => (await api.get<AdSpend[]>('/ad-spends')).data })

export function useSaveAd() {
  const invalidate = useDomainInvalidation()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/ad-spends/${id}`, body)).data : (await api.post('/ad-spends', body)).data,
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['ads'] })
    },
  })
}

export function useDeleteAd() {
  const invalidate = useDomainInvalidation()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/ad-spends/${id}`),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['ads'] })
    },
  })
}

// ---- Canais / e-commerces ----
export const useChannels = () =>
  useQuery({ queryKey: ['channels'], queryFn: async () => (await api.get<Channel[]>('/channels')).data })

export function useSaveChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: any) =>
      id ? (await api.patch(`/channels/${id}`, body)).data : (await api.post('/channels', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['channels'] }),
  })
}

export function useDeleteChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/channels/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['channels'] })
      qc.invalidateQueries({ queryKey: ['sales'] })
    },
  })
}

// ---- Imports (exports do marketplace) ----
export const useImportsStatus = () =>
  useQuery({ queryKey: ['imports'], queryFn: async () => (await api.get('/imports')).data })

export function useImportOrders() {
  const invalidate = useDomainInvalidation()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const fd = new FormData()
      fd.append('file', file)
      return (await api.post('/imports/orders', fd, { params: { dry_run: dryRun } })).data
    },
    onSuccess: (_d, vars) => {
      if (!vars.dryRun) {
        invalidate()
        qc.invalidateQueries({ queryKey: ['imports'] })
        qc.invalidateQueries({ queryKey: ['mappings-pendentes'] })
      }
    },
  })
}

export function useImportAds() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const fd = new FormData()
      fd.append('file', file)
      return (await api.post('/imports/ads', fd, { params: { dry_run: dryRun } })).data
    },
    onSuccess: (_d, vars) => {
      if (!vars.dryRun) qc.invalidateQueries({ queryKey: ['imports'] })
    },
  })
}

// ---- Vínculo de SKUs ----
export const usePendingMappings = () =>
  useQuery({
    queryKey: ['mappings-pendentes'],
    queryFn: async () => (await api.get('/mappings/pendentes')).data,
  })

export const useMappings = () =>
  useQuery({ queryKey: ['mappings'], queryFn: async () => (await api.get('/mappings')).data })

export function useCreateMapping() {
  const invalidate = useDomainInvalidation()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { match_key: string; product_id?: number | null; kit_id?: number | null }) =>
      (await api.post('/mappings', body)).data,
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['mappings-pendentes'] })
      qc.invalidateQueries({ queryKey: ['mappings'] })
      qc.invalidateQueries({ queryKey: ['imports'] })
    },
  })
}

export function useDeleteMapping() {
  const invalidate = useDomainInvalidation()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/mappings/${id}`),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['mappings-pendentes'] })
      qc.invalidateQueries({ queryKey: ['mappings'] })
    },
  })
}

// ---- Precificação ----
export function useSimulatePricing() {
  return useMutation({
    mutationFn: async (body: any) => (await api.post<PricingResult>('/pricing/simulate', body)).data,
  })
}

// ---- Usuários (equipe) ----
export const useUsers = () =>
  useQuery({ queryKey: ['users'], queryFn: async () => (await api.get<User[]>('/auth/users')).data })

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: any) => (await api.post('/auth/users', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useResetUserPassword() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, password }: { id: number; password: string }) =>
      (await api.patch(`/auth/users/${id}/password`, { password })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => api.delete(`/auth/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}
