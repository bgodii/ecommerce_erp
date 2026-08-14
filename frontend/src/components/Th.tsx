/** Cabeçalho de tabela com descrição no hover (tooltip nativo + indicação visual). */
export default function Th({
  label,
  help,
  num,
}: {
  label: string
  help?: string
  num?: boolean
}) {
  return (
    <th className={num ? 'num' : undefined} title={help}>
      {help ? <span className="th-help">{label}</span> : label}
    </th>
  )
}
