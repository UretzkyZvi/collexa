"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Project = { id: string; name: string };

interface ProjectContextValue {
  projects: Project[];
  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;
  addProject: (name: string) => void;
}

const ProjectContext = createContext<ProjectContextValue | undefined>(undefined);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // In lieu of backend endpoints, persist to localStorage as a basic placeholder
  useEffect(() => {
    try {
      const raw = localStorage.getItem("collexa_projects");
      const parsed = raw ? (JSON.parse(raw) as Project[]) : [];
      setProjects(parsed);
      const sel = localStorage.getItem("collexa_selected_project_id");
      setSelectedProjectId(sel || null);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("collexa_projects", JSON.stringify(projects));
    } catch {}
  }, [projects]);

  useEffect(() => {
    try {
      if (selectedProjectId) localStorage.setItem("collexa_selected_project_id", selectedProjectId);
      else localStorage.removeItem("collexa_selected_project_id");
    } catch {}
  }, [selectedProjectId]);

  const addProject = (name: string) => {
    const id = `proj_${Math.random().toString(36).slice(2, 10)}`;
    setProjects((prev) => [...prev, { id, name }]);
    setSelectedProjectId(id);
  };

  const value = useMemo(
    () => ({ projects, selectedProjectId, setSelectedProjectId, addProject }),
    [projects, selectedProjectId]
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProjectContext must be used within ProjectProvider");
  return ctx;
}

