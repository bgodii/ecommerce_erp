export const fmtBRL = (v: number | null | undefined): string =>
  (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

export const fmtNum = (v: number | null | undefined, d = 0): string =>
  (v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d })

export const fmtPct = (v: number | null | undefined, d = 1): string =>
  ((v ?? 0) * 100).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }) +
  '%'

export const fmtDate = (s: string | null | undefined): string => {
  if (!s) return ''
  const iso = s.length <= 10 ? `${s}T00:00:00` : s
  const d = new Date(iso)
  return isNaN(d.getTime()) ? String(s) : d.toLocaleDateString('pt-BR')
}

export const todayISO = (): string => new Date().toISOString().slice(0, 10)
