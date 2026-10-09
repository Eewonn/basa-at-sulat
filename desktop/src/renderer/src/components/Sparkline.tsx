// Tiny trend line: no chart library needed.
export function Sparkline({ values, width = 320, height = 90 }: { values: number[]; width?: number; height?: number }) {
  if (values.length < 2) return null
  const min = Math.min(...values) - 5
  const max = Math.max(...values) + 5
  const pts = values.map((v, i) => [(i / (values.length - 1)) * (width - 16) + 8, height - 8 - ((v - min) / (max - min)) * (height - 16)])
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const [lx] = pts[pts.length - 1]
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <path d={`${line} L${lx} ${height} L8 ${height} Z`} fill="#E4E9FF" />
      <path d={line} fill="none" stroke="#3D63E8" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === pts.length - 1 ? 7 : 4} fill={i === pts.length - 1 ? '#EE4466' : '#3D63E8'} stroke="#fff" strokeWidth="2" />
      ))}
    </svg>
  )
}
