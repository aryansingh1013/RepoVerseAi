import { ChevronLeft, ChevronRight, LogOut } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import { useAuth } from "@/hooks/useAuth";
import { SPACE_OBJECT_LABELS } from "@/types";

/**
 * "Navigation is exploration, not opening panels" — this is the one piece
 * of chrome over the 3D view: a breadcrumb of the journey so far, and a
 * back control. Everything else is driven by clicking objects in space.
 */
export function NavigationHud() {
  const { breadcrumbs, jumpTo, goBack, isTransitioning } = useNavigation();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const canGoBack = breadcrumbs.length > 1;

  const handleSignOut = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

  return (
    <div className="pointer-events-none absolute top-4 left-4 right-4 flex items-center gap-2 z-10">
      <button
        onClick={goBack}
        disabled={!canGoBack}
        aria-label="Go back"
        className="pointer-events-auto flex items-center justify-center h-8 w-8 rounded-md border border-white/10 bg-void-900/70 text-mist-300 backdrop-blur transition-colors hover:bg-void-700/70 hover:text-mist-100 disabled:opacity-30 disabled:hover:bg-void-900/70"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div className="pointer-events-auto flex items-center gap-1.5 rounded-md border border-white/10 bg-void-900/70 px-3 py-1.5 backdrop-blur overflow-x-auto">
        {breadcrumbs.map((crumb, i) => {
          const isLast = i === breadcrumbs.length - 1;
          return (
            <span key={crumb.id} className="flex items-center gap-1.5 shrink-0">
              {i > 0 && <ChevronRight className="h-3 w-3 text-mist-700" />}
              <button
                onClick={() => !isLast && jumpTo(crumb.id)}
                className={
                  isLast
                    ? "text-xs font-mono text-mist-100"
                    : "text-xs font-mono text-mist-500 hover:text-signal-400 transition-colors"
                }
              >
                {crumb.name}
              </button>
              <span className="text-[9px] uppercase tracking-wide text-mist-700">
                {SPACE_OBJECT_LABELS[crumb.kind]}
              </span>
            </span>
          );
        })}
      </div>

      <AnimatePresence>
        {isTransitioning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="pointer-events-none rounded-md border border-white/10 bg-void-900/70 px-2.5 py-1.5 text-[10px] font-mono text-signal-400 backdrop-blur animate-pulse-slow"
          >
            traveling…
          </motion.div>
        )}
      </AnimatePresence>

      {/* Spacer to push user chip to the far right */}
      <div className="flex-1" />

      {/* User chip + sign out */}
      {user && (
        <div className="pointer-events-auto flex items-center gap-2 rounded-md border border-white/10 bg-void-900/70 pl-2.5 pr-1.5 py-1 backdrop-blur">
          <span
            className="text-[10px] font-mono text-mist-400 truncate max-w-[160px]"
            title={user.email ?? user.id}
          >
            {user.email ?? user.id.slice(0, 8)}
          </span>
          <button
            onClick={handleSignOut}
            aria-label="Sign out"
            title="Sign out"
            className="flex items-center justify-center h-6 w-6 rounded border border-white/10 text-mist-500 hover:text-red-300 hover:border-red-400/40 transition-colors"
          >
            <LogOut className="h-3 w-3" />
          </button>
        </div>
      )}
    </div>
  );
}
