import type { ReactElement } from 'react'
import Dashboard from './pages/Dashboard'
import PredictionDashboard from './pages/PredictionDashboard'
import ProjectCreation from './pages/ProjectCreation'
import RequirementInput from './pages/RequirementInput'
import ArchitectureBuilder from './pages/ArchitectureBuilder'
import ArchitectureComparison from './pages/ArchitectureComparison'
import RecommendationView from './pages/RecommendationView'
import ShapExplanation from './pages/ShapExplanation'
import WhatIfAnalysis from './pages/WhatIfAnalysis'
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
  { path: '/projects/new', label: 'Project Creation', element: <ProjectCreation /> },
  { path: '/requirements', label: 'Requirement Input', element: <RequirementInput /> },
  { path: '/architecture-builder', label: 'Architecture Builder', element: <ArchitectureBuilder /> },
  { path: '/compare', label: 'Architecture Comparison', element: <ArchitectureComparison /> },
  { path: '/simulation', label: 'Simulation Configuration', element: todo('Simulation Configuration', 'Define the workload and run the simulation.') },
  { path: '/predictions', label: 'Prediction Dashboard', element: <PredictionDashboard /> },
  { path: '/what-if', label: 'What-If Analysis', element: <WhatIfAnalysis /> },
  { path: '/recommendations', label: 'Recommendation View', element: <RecommendationView /> },
  { path: '/explanations', label: 'SHAP Explanation', element: <ShapExplanation /> },
  { path: '/advisor', label: 'RAG / LLM Advisor', element: todo('RAG / LLM Advisor', 'Evidence-grounded explanation with citations.') },
  { path: '/experiments', label: 'Experiment History', element: todo('Experiment History', 'Past experiments and runs.') },
  { path: '/validation', label: 'Model / Validation Results', element: todo('Model / Validation Results', 'Model quality and prediction-vs-observation checks.') },
]
