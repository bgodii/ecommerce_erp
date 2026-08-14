import { PERIOD_PRESETS, Period } from '../lib/periods'

/** Seletor de período: botões de preset + intervalo customizado por data. */
export default function PeriodPicker({
  value,
  onChange,
  preset,
  onPreset,
}: {
  value: Period
  onChange: (p: Period) => void
  preset: string
  onPreset: (key: string) => void
}) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {PERIOD_PRESETS.map((p) => (
          <button
            key={p.key}
            className={`btn sm ${preset === p.key ? '' : 'secondary'}`}
            onClick={() => {
              onPreset(p.key)
              onChange(p.calc())
            }}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="field" style={{ margin: 0 }}>
        <label>De</label>
        <input
          type="date"
          value={value.from}
          onChange={(e) => {
            onPreset('custom')
            onChange({ ...value, from: e.target.value })
          }}
        />
      </div>
      <div className="field" style={{ margin: 0 }}>
        <label>Até</label>
        <input
          type="date"
          value={value.to}
          onChange={(e) => {
            onPreset('custom')
            onChange({ ...value, to: e.target.value })
          }}
        />
      </div>
    </div>
  )
}
