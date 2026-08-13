import { useMemo, useState } from 'react'

export type SortDir = 'asc' | 'desc'

export interface SortState<T> {
  sorted: T[]
  sortKey: keyof T | undefined
  dir: SortDir
  toggle: (k: keyof T) => void
}

// Ordenação client-side genérica. Datas ISO (YYYY-MM-DD) ordenam corretamente como string.
export function useSort<T>(
  rows: T[] | undefined,
  initialKey?: keyof T,
  initialDir: SortDir = 'asc',
): SortState<T> {
  const [sortKey, setSortKey] = useState<keyof T | undefined>(initialKey)
  const [dir, setDir] = useState<SortDir>(initialDir)

  const sorted = useMemo(() => {
    const data = rows ? [...rows] : []
    if (!sortKey) return data
    data.sort((a, b) => {
      const av = a[sortKey] as unknown
      const bv = b[sortKey] as unknown
      let cmp: number
      if (av == null && bv == null) cmp = 0
      else if (av == null) cmp = -1
      else if (bv == null) cmp = 1
      else if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv
      else cmp = String(av).localeCompare(String(bv), 'pt-BR')
      return dir === 'asc' ? cmp : -cmp
    })
    return data
  }, [rows, sortKey, dir])

  function toggle(k: keyof T) {
    if (sortKey === k) {
      setDir(dir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(k)
      setDir('asc')
    }
  }

  return { sorted, sortKey, dir, toggle }
}

export function SortTh<T>({
  label,
  k,
  sort,
  num,
}: {
  label: string
  k: keyof T
  sort: SortState<T>
  num?: boolean
}) {
  const active = sort.sortKey === k
  return (
    <th className={`sortable${num ? ' num' : ''}`} onClick={() => sort.toggle(k)}>
      {label}
      <span className={`sort-ind${active ? ' active' : ''}`}>
        {active ? (sort.dir === 'asc' ? '▲' : '▼') : '⇅'}
      </span>
    </th>
  )
}
