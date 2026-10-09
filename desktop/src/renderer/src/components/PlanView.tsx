// A group's draft plan (GET /class), laid out from its text. The engine writes it as lines:
// "Pamagat: …", "Kailangan: …", "Mga Hakbang:", "1. …", "Pagsusuri: …", and maybe the model's example sentence last.
type Line = { label: string; value: string } | { step: string }

function parse(plan: string): Line[] {
  return plan
    .split('\n')
    .filter((l) => l.trim())
    .map((l) => {
      const step = l.match(/^\d+\.\s*(.*)$/)
      if (step) return { step: step[1] }
      const i = l.indexOf(':')
      return i < 0 ? { label: '', value: l } : { label: l.slice(0, i).trim(), value: l.slice(i + 1).trim() }
    })
}

export function PlanView({ plan }: { plan: string }) {
  const [first, ...rest] = parse(plan)
  const steps = rest.flatMap((l) => ('step' in l ? [l.step] : []))
  const fields = rest.filter((l): l is { label: string; value: string } => !('step' in l))
  const title = first && !('step' in first) ? first.value : null
  const stepsAt = rest.findIndex((l) => 'step' in l)

  const field = (f: { label: string; value: string }) => {
    if (!f.value) return null // the "Mga Hakbang:" heading; the steps carry it
    // The model's example sentence is for reading aloud, so it gets its own card.
    if (f.label.startsWith('Halimbawang') || f.label.startsWith('Example')) {
      return (
        <div key={f.label} className="rounded-tile bg-white p-3 ring-1 ring-line">
          <p className="text-xs font-extrabold tracking-wider text-muted uppercase">{f.label}</p>
          <p className="mt-1 text-lg leading-snug font-black text-navy">“{f.value}”</p>
        </div>
      )
    }
    return (
      <p key={f.label} className="leading-snug">
        <span className="font-extrabold text-navy">{f.label}: </span>
        <span className="font-semibold text-body">{f.value}</span>
      </p>
    )
  }
  const stepsHeading = fields.find((f) => !f.value)?.label

  return (
    <div className="mt-3 flex flex-col gap-3 select-text">
      {title && <p className="text-lg font-black text-navy">{title}</p>}
      {fields.filter((f) => rest.indexOf(f) < stepsAt || stepsAt < 0).map(field)}
      {steps.length > 0 && (
        <div>
          {stepsHeading && <p className="font-extrabold text-navy">{stepsHeading}</p>}
          <ol className="mt-1.5 flex flex-col gap-2">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-navy text-xs font-black text-white">{i + 1}</span>
                <span className="font-semibold leading-snug text-body">{s}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
      {stepsAt >= 0 && fields.filter((f) => rest.indexOf(f) > stepsAt).map(field)}
    </div>
  )
}
