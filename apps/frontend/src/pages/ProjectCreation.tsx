import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useCurrentProject } from '../features/projects/useCurrentProject'

const projectSchema = z.object({
  name: z.string().trim().min(2, 'Give the project a name (at least 2 characters)'),
  description: z.string().optional(),
})
type ProjectForm = z.infer<typeof projectSchema>

export default function ProjectCreation() {
  const { project, createProject } = useCurrentProject()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectForm>({ resolver: zodResolver(projectSchema) })

  const onSubmit = (values: ProjectForm) => {
    createProject(values.name, values.description)
    navigate('/requirements')
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold">Project Creation</h1>
      <p className="mt-2 text-slate-600">A project holds your requirements, architectures and experiments.</p>

      {project && (
        <p className="mt-4 rounded border border-slate-200 bg-white px-4 py-2 text-sm">
          Current project: <strong>{project.name}</strong>. Creating a new one replaces it.
        </p>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="name" className="block text-sm font-medium">Project name</label>
          <input id="name" {...register('name')} className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2" />
          {errors.name && <p role="alert" className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium">Description (optional)</label>
          <textarea id="description" rows={3} {...register('description')} className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2" />
        </div>
        <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-white hover:bg-slate-700">
          Create project
        </button>
      </form>
    </div>
  )
}