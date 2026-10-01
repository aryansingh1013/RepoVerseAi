import { useEffect } from "react";
import { useNavigation } from "@/hooks/useNavigation";

/**
 * Handles keyboard interaction (Escape to go back/return to repository overview)
 * and selection lifecycle.
 */
export function useSelectionKeyboard() {
  const { goBack, focusId, spaceGraph, navigateTo } = useNavigation();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input or textarea
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        const rootNode = spaceGraph.find((o) => o.parentId === null);
        const rootId = rootNode?.id || "repository-root";

        if (focusId !== rootId) {
          goBack();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [focusId, spaceGraph, goBack, navigateTo]);
}
