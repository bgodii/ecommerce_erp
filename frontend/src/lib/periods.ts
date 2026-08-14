/** Presets de período usados nos relatórios (últimos 7 dias, este mês, mês passado…). */
const iso = (d: Date) => d.toISOString().slice(0, 10)

export const daysAgoISO = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return iso(d)
}

export interface Period {
  from: string
  to: string
}

export const PERIOD_PRESETS: { key: string; label: string; calc: () => Period }[] = [
  {
    key: '7d',
    label: 'Últimos 7 dias',
    calc: () => ({ from: daysAgoISO(6), to: iso(new Date()) }),
  },
  {
    key: '30d',
    label: 'Últimos 30 dias',
    calc: () => ({ from: daysAgoISO(29), to: iso(new Date()) }),
  },
  {
    key: 'mes',
    label: 'Este mês',
    calc: () => {
      const n = new Date()
      return { from: iso(new Date(n.getFullYear(), n.getMonth(), 1)), to: iso(n) }
    },
  },
  {
    key: 'mes-1',
    label: 'Mês passado',
    calc: () => {
      const n = new Date()
      return {
        from: iso(new Date(n.getFullYear(), n.getMonth() - 1, 1)),
        to: iso(new Date(n.getFullYear(), n.getMonth(), 0)),
      }
    },
  },
]
