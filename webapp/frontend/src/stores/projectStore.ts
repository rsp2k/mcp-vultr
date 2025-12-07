import { persistentAtom } from '@nanostores/persistent';

export interface Project {
  id: string;
  name: string;
  description?: string;
}

/**
 * Persistent project store using nanostores
 * Automatically syncs to localStorage and persists across page loads
 */
export const currentProject = persistentAtom<Project | null>(
  'currentProject',
  null,
  {
    encode: JSON.stringify,
    decode: (str) => {
      try {
        return JSON.parse(str);
      } catch {
        return null;
      }
    },
  }
);

/**
 * Helper to check if a project is selected
 */
export function hasProject(): boolean {
  return currentProject.get() !== null;
}

/**
 * Helper to get current project ID
 */
export function getProjectId(): string | null {
  return currentProject.get()?.id ?? null;
}
