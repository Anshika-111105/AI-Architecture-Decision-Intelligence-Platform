import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useCurrentProject } from '../features/projects/useCurrentProject'
import { DOMAINS, requirementsSchema, type RequirementsForm } from '../types/requirements.zod'
import type { RequirementAnalysisResponse } from '../types/analysis'

type NumericField = Exclude<keyof RequirementsForm, 'project_id' | 'domain'>

const FIELDS: { name: NumericField; label: string; hint: string; step?: string; optional?: boolean }[] = [
  { name: 'users', label: 'Users', hint: 'Total registered users' },
  { name: 'concurrency', label: 'Concurrent users', hint: 'Active at the same time; cannot exceed users' },
  { name: 'rps', label: 'Baseline RPS', hint: 'Requests per second, normal load', step: 'any' },
  { name: 'peak_rps', label: 'Peak RPS', hint: 'Requests per second at peak; at least the baseline', step: 'any' },
  { name: 'data_size', label: 'Data size (GB)', hint: 'Total data volume', step: 'any' },
  { name: 'read_write_ratio', label: 'Read ratio (0 to 1)', hint: '0.8 means 80% reads', step: 'any' },
  { name: 'latency_sla', label: 'Latency SLA (ms)', hint: 'Maximum acceptable latency', step: 'any' },
  { name: 'availability_sla', label: 'Availability SLA (%)', hint: 'Between 90 and 100, e.g. 99.9', step: 'any' },
  { name: 'budget', label: 'Monthly budget (USD)', hint: 'Infrastructure budget per month', step: 'any' },
  { name: 'traffic_growth', label: 'Traffic growth (% per year)', hint: 'Optional', step: 'any', optional: true },
  { name: 'team_size', label: 'Team size', hint: 'Optional', optional: true },
]

// The backend extractor and the JSON schema spell one domain differently.
const DOMAIN_ALIASES: Record<string, string> = { ecommerce: 'e-commerce' }

export default function RequirementInput() {
  const { project } = useCurrentProject()
  const [text, setText] = useState('')
  const [analysis, setAnalysis] = useState<RequirementAnalysisResponse | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<RequirementsForm>({
    resolver: zodResolver(requirementsSchema),
    defaultValues: { project_id: project?.id ?? '', domain: 'e-commerce' },
  })

  const save = useMutation({
    mutationFn: (body: RequirementsForm) =>
      api<RequirementsForm>('/requirements', { method: 'POST', body: JSON.stringify(body) }),
  })

  const analyze = useMutation({
    mutationFn: (raw: string) =>
      api<RequirementAnalysisResponse>('/requirements/analyze', {
        method: 'POST',
        body: JSON.stringify({ text: raw }),
      }),
    onSuccess: (result) => {
      setAnalysis(result)
      // Fill only what was found; null means "not mentioned" and must stay empty.
      const found = result.requirements
      const domain = found.domain ? (DOMAIN_ALIASES[found.domain] ?? found.domain) : undefined
      if (domain && (DOMAINS as readonly string[]).includes(domain)) {
        setValue('domain', domain as RequirementsForm['domain'])
      }
      for (const f of FIELDS) {
        const v = found[f.name]
        if (typeof v === 'number') setValue(f.name, v, { shouldValidate: true })
      }
    },
  })

  if (!project) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Requirement Input</h1>
        <p className="mt-2 text-slate-600">
          Create a project first so the requirements have somewhere to live.{' '}
          <Link to="/projects/new" className="font-medium underline">Create a project</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">Requirement Input</h1>
      <p className="mt-2 text-slate-600">Project: <strong>{project.name}</strong></p>

      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="font-medium">Describe your system (optional)</h2>
        <p className="mt-1 text-sm text-slate-600">
          Write it in plain language and we will fill in what we can find. You review everything below.
        </p>
        <textarea
          aria-label="Describe your system"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="An online shop with 100k users, about 500 requests per second, 200 ms latency target and a $5000 monthly budget"
          className="mt-3 w-full rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          disabled={!text.trim() || analyze.isPending}
          onClick={() => analyze.mutate(text)}
          className="mt-2 rounded border border-slate-900 px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-50"
        >
          {analyze.isPending ? 'Analyzing...' : 'Analyze text'}
        </button>
        {analyze.isError && <p role="alert" className="mt-2 text-sm text-red-600">Analysis failed: {analyze.error.message}</p>}
        {analysis && (
          <div className="mt-3 space-y-2 rounded bg-slate-50 p-3 text-sm">
            {analysis.missing_fields.length > 0 && (
              <p><strong>Not mentioned (please fill in):</strong> {analysis.missing_fields.join(', ')}</p>
            )}
            {analysis.assumptions.length > 0 && (
              <ul className="list-disc pl-5">
                {analysis.assumptions.map((a) => <li key={a}>{a}</li>)}
              </ul>
            )}
          </div>
        )}
      </section>

      <form onSubmit={handleSubmit((v) => save.mutate(v))} noValidate className="mt-6 space-y-4">
        <div>
          <label htmlFor="domain" className="block text-sm font-medium">Domain</label>
          <select id="domain" {...register('domain')} className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2">
            {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {FIELDS.map((f) => (
            <div key={f.name}>
              <label htmlFor={f.name} className="block text-sm font-medium">{f.label}</label>
              <input
                id={f.name}
                type="number"
                step={f.step}
                {...register(f.name, { setValueAs: (v) => (v === '' || v == null ? undefined : Number(v)) })}
                className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"
              />
              <p className="mt-1 text-xs text-slate-500">{f.hint}</p>
              {errors[f.name] && <p role="alert" className="text-sm text-red-600">{errors[f.name]?.message}</p>}
            </div>
          ))}
        </div>

        <button type="submit" disabled={save.isPending} className="rounded bg-slate-900 px-4 py-2 text-white hover:bg-slate-700 disabled:opacity-50">
          {save.isPending ? 'Saving...' : 'Save requirements'}
        </button>
        {save.isError && <p role="alert" className="text-sm text-red-600">Could not save: {save.error.message}</p>}
        {save.isSuccess && (
          <p className="rounded border border-green-300 bg-green-50 px-4 py-2 text-sm text-green-900">
            Requirements saved. Next: <Link to="/architecture-builder" className="font-medium underline">design an architecture</Link>.
          </p>
        )}
      </form>
    </div>
  )
}