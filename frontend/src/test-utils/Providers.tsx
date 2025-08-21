import React from 'react';
import { ProjectProvider } from '~/hooks/project-context';

export function Providers({ children }: { children: React.ReactNode }) {
  return <ProjectProvider>{children}</ProjectProvider>;
}

