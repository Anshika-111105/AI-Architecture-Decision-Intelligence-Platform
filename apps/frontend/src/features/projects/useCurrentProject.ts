import { useState } from 'react'

export interface Project {
  id: string
  name: string
  description?: string
  created_at: string
}

const KEY = 'adip.currentProject'

// PLACEHOLDER: until the FastAPI /projects routes exist, the current project
// lives in this browser's localStorage. Swap these two functions for API calls later.
function load(): Project | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Project) : null
  } catch {
    return null
  }
}

function save(project: Project) {
  try {
    localStorage.setItem(KEY, JSON.stringify(project))
  } catch {
    /* storage unavailable: the project just won't survive a reload */
  }
}

export function useCurrentProject() {
  const [project, setProject] = useState<Project | null>(load)

  function createProject(name: string, description?: string): Project {
    const p: Project = {
      id: crypto.randomUUID(),
      name: name.trim(),
      description: description?.trim() || undefined,
      created_at: new Date().toISOString(),
    }
    save(p)
    setProject(p)
    return p
  }

  return { project, createProject }
}