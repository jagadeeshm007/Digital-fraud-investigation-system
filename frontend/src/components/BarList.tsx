// Simple bar + number list (design-system mapping: "simple bar built with divs, plus a table alternative").
export default function BarList({
  data,
  tone = () => 'bg-primary',
  empty = 'No data yet',
}: {
  data: Record<string, number>
  tone?: (key: string) => string
  empty?: string
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map(([, v]) => v))
  if (entries.length === 0) return <p className="text-muted-foreground text-sm">{empty}</p>
  return (
    <table className="w-full table-fixed text-sm">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <th scope="row" className="w-[45%] py-1 pr-3 text-left font-normal text-muted-foreground">
              <span className="block truncate capitalize" title={key}>
                {key.replaceAll('_', ' ')}
              </span>
            </th>
            <td className="py-1">
              <span className="block h-2.5 rounded-full bg-muted">
                <span
                  className={`block h-2.5 rounded-full ${tone(key)}`}
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </span>
            </td>
            <td className="w-10 py-1 text-right font-mono tabular-nums">{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
