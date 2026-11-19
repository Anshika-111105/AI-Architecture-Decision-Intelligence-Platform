import type { ReactElement } from 'react'
import Dashboard from './pages/Dashboard'
import PredictionDashboard from './pages/PredictionDashboard'
import PlaceholderPage from './components/PlaceholderPage'

export interface AppRoute {
  path: string
  label: string
  element: ReactElement
}

const todo = (title: string, readme: string) => (
  <PlaceholderPage title={title} description={readme} />
)

// One entry per main screen listed in README section 24.
export const appRoutes: AppRoute[] = [
  { path: '/', label: 'Dashboard', element: <Dashboard /> },
  { path: '/projects/new', label: 'Project Creation', element: todo('Project Creation', 'Create a project to hold requirements, architectures and experiments.') },
  { path: '/requirements', label: 'Requirement Input', element: todo('Requirement Input', 'Form + natural-language input, validated against the requirements schema.') },
  { path: '/architecture-builder', label: 'Architecture Builder', element: todo('Architecture Builder', 'React Flow canvas that exports an architecture graph.') },
  { path: '/compare', label: 'Architecture Comparison', element: todo('Architecture Comparison', 'Side-by-side metrics and radar chart.') },
  { path: '/simulation', label: 'Simulation Configuration', element: todo('Simulation Configuration', 'Define the workload and run the simulation.') },
  { path: '/predictions', label: 'Prediction Dashboard', element: <PredictionDashboard /> },
  { path: '/what-if', label: 'What-If Analysis', element: todo('What-If Analysis', 'Sliders for RPS, replicas, cache and more, with recalculated metrics.') },
  { path: '/recommendations', label: 'Recommendation View', element: todo('Recommendation View', 'Pareto frontier and TOPSIS ranking with adjustable weights.') },
  { path: '/explanations', label: 'SHAP Explanation', element: todo('SHAP Explanation', 'Feature contributions behind each prediction.') },
  { path: '/advisor', label: 'RAG / LLM Advisor', element: todo('RAG / LLM Advisor', 'Evidence-grounded explanation with citations.') },
  { path: '/experiments', label: 'Experiment History', element: todo('Experiment History', 'Past experiments and runs.') },
  { path: '/validation', label: 'Model / Validation Results', element: todo('Model / Validation Results', 'Model quality and prediction-vs-observation checks.') },
]
