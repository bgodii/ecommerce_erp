/** Presets de período usados nos relatórios. */
const iso = (d: Date) => d.toISOString().slice(0, 10)

export const daysAgoISO = (n: number) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return iso(d)
}

/** Domingo da semana de `ref` (semana começa no domingo, como no Brasil). */
const domingoDaSemana = (ref: Date) => {
  const d = new Date(ref)
  d.setDate(d.getDate() - d.getDay()) // getDay(): 0 = domingo
  return d
}

export interface Period {
  from: string
  to: string
}

export const PERIOD_PRESETS: { key: string; label: string; calc: () => Period }[] = [
  {
    key: 'hoje',
    label: 'Hoje',
    calc: () => ({ from: iso(new Date()), to: iso(new Date()) }),
  },
  {
    key: 'ontem',
    label: 'Ontem',
    calc: () => ({ from: daysAgoISO(1), to: daysAgoISO(1) }),
  },
  {
    key: 'semana',
    label: 'Esta semana',
    calc: () => {
      const dom = domingoDaSemana(new Date())
      return { from: iso(dom), to: iso(new Date()) }
    },
  },
  {
    key: 'semana-1',
    label: 'Semana passada',
    calc: () => {
      const domAtual = domingoDaSemana(new Date())
      const domAnterior = new Date(domAtual)
      domAnterior.setDate(domAnterior.getDate() - 7)
      const sabAnterior = new Date(domAtual)
      sabAnterior.setDate(sabAnterior.getDate() - 1)
      return { from: iso(domAnterior), to: iso(sabAnterior) }
    },
  },
  {
    key: '7d',
    label: '7 dias',
    calc: () => ({ from: daysAgoISO(6), to: iso(new Date()) }),
  },
  {
    key: '30d',
    label: '30 dias',
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

/** Índice do preset padrão (30 dias) — usado como estado inicial das telas. */
export const DEFAULT_PRESET = PERIOD_PRESETS.findIndex((p) => p.key === '30d')
