import { createContext, useContext, useState, useMemo, type ReactNode, createElement } from "react";

interface SelectedObjectContextValue {
  selectedId: string | null;
  hoveredId: string | null;
  select: (id: string | null) => void;
  hover: (id: string | null) => void;
}

const SelectedObjectContext = createContext<SelectedObjectContextValue | null>(null);

export function SelectedObjectProvider({ children }: { children: ReactNode }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const value = useMemo(
    () => ({
      selectedId,
      hoveredId,
      select: setSelectedId,
      hover: setHoveredId,
    }),
    [selectedId, hoveredId]
  );

  return createElement(SelectedObjectContext.Provider, { value }, children);
}

export function useSelectedObject() {
  const ctx = useContext(SelectedObjectContext);
  if (!ctx) {
    throw new Error("useSelectedObject must be used within a SelectedObjectProvider");
  }
  return ctx;
}
