import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TopNavbar } from "./TopNavbar";
import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { ChatBotPanel } from "./ChatBotPanel";
import { Sparkles } from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const {
    isMissionControlOpen,
    setMissionControlOpen,
    displayedId,
    spaceGraph
  } = useNavigation();

  // Find root ID dynamically
  const rootId = spaceGraph.find((o) => o.parentId === null)?.id ?? "galaxy-root";

  // Active interaction: either a planet/star is selected, or the chatbot is explicitly opened via the orb
  const isInteractionActive = (displayedId !== rootId) || isMissionControlOpen;

  return (
    <div className="relative h-screen w-screen bg-void-950 text-mist-100 overflow-hidden font-body select-none">
      {isInteractionActive ? (
        // Split Column Dashboard Layout
        <div className="flex h-full w-full bg-void-950 text-mist-100 overflow-hidden font-body select-none">
          {/* Left Panel */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="w-80 shrink-0 border-r border-white/5 bg-void-900/40 backdrop-blur-md flex flex-col h-full z-10 p-3"
          >
            <LeftSidebar />
          </motion.div>

          {/* Middle Part (Galaxy Scene + Chatbot Panel) */}
          <div className="flex-1 flex flex-col h-full min-w-0 relative">
            {/* Upper Part: Galaxy Canvas */}
            <div className="flex-1 min-h-0 relative">
              <main className="absolute inset-0 pointer-events-auto z-0">
                {children}
              </main>
              {/* Floating Top Navbar inside the middle panel */}
              <div className="absolute top-4 left-1/2 -translate-x-1/2 w-[90%] max-w-4xl z-20 pointer-events-none">
                <TopNavbar />
              </div>
            </div>

            {/* Lower Part: Integrated Chatbot Panel */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 120 }}
              className="h-[38vh] shrink-0 p-3 border-t border-white/5 bg-void-900/50 backdrop-blur-md flex flex-col z-10"
            >
              <ChatBotPanel />
            </motion.div>
          </div>

          {/* Right Panel */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            className="w-80 shrink-0 border-l border-white/5 bg-void-900/40 backdrop-blur-md flex flex-col h-full z-10 p-3"
          >
            <RightPanel />
          </motion.div>
        </div>
      ) : (
        // Fullscreen Starfield Explorer View
        <div className="absolute inset-0 z-0 h-full w-full">
          {/* Main 3D Canvas */}
          <main className="absolute inset-0 z-0 h-full w-full pointer-events-auto">
            {children}
          </main>

          {/* Top Navbar */}
          <div className="absolute top-4 left-1/2 -translate-x-1/2 w-[90%] max-w-4xl z-20 pointer-events-none">
            <TopNavbar />
          </div>

          {/* Floating AI Orb at bottom center */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-auto">
            <motion.button
              layoutId="ai-orb"
              onClick={() => setMissionControlOpen(true)}
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.95 }}
              className="relative flex items-center justify-center h-16 w-16 rounded-full border border-signal-400/40 bg-void-950/80 shadow-glow backdrop-blur-md cursor-pointer group animate-pulse-slow"
            >
              <div className="absolute inset-0.5 rounded-full bg-gradient-to-tr from-signal-600/20 to-signal-400/40 animate-pulse" />
              <Sparkles className="h-6 w-6 text-signal-400 group-hover:rotate-12 transition-transform duration-300" strokeWidth={1.5} />
              
              <span className="absolute -inset-1 rounded-full border border-signal-400/20 animate-ping opacity-60 pointer-events-none" />
              <span className="absolute -inset-3 rounded-full border border-signal-500/10 animate-pulse-slow pointer-events-none" />
            </motion.button>
          </div>
        </div>
      )}
    </div>
  );
}
