import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TopNavbar } from "./TopNavbar";
import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { ChatBotPanel } from "./ChatBotPanel";
import { SkillsOverlay } from "./SkillsOverlay";
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
    spaceGraph,
    showSkillsPanel
  } = useNavigation();

  // Resizing state variables (in pixels)
  const [leftWidth, setLeftWidth] = useState(320);
  const [rightWidth, setRightWidth] = useState(320);
  const [chatHeight, setChatHeight] = useState(280);

  // Resize handlers
  const handleLeftResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = leftWidth;
    
    const onMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      setLeftWidth(Math.max(240, Math.min(600, startWidth + deltaX)));
    };
    
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  const handleRightResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightWidth;
    
    const onMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      setRightWidth(Math.max(240, Math.min(600, startWidth - deltaX)));
    };
    
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  const handleChatResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = chatHeight;
    
    const onMouseMove = (moveEvent: MouseEvent) => {
      const deltaY = moveEvent.clientY - startY;
      setChatHeight(Math.max(150, Math.min(650, startHeight - deltaY)));
    };
    
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

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
            style={{ width: leftWidth }}
            className="relative shrink-0 border-r border-white/5 bg-void-900/40 backdrop-blur-md flex flex-col h-full z-10 p-3"
          >
            <LeftSidebar />
            {/* Right border resize handle */}
            <div
              onMouseDown={handleLeftResize}
              className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-signal-500/40 active:bg-signal-500/80 transition-colors z-20"
            />
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

              {/* Skills Panel Overlay */}
              <AnimatePresence>
                {showSkillsPanel && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="absolute inset-0 pointer-events-none"
                  >
                    <SkillsOverlay />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Lower Part: Integrated Chatbot Panel */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 120 }}
              style={{ height: chatHeight }}
              className="relative shrink-0 p-3 border-t border-white/5 bg-void-900/50 backdrop-blur-md flex flex-col z-10"
            >
              {/* Top border resize handle */}
              <div
                onMouseDown={handleChatResize}
                className="absolute top-0 left-0 w-full h-1 cursor-row-resize hover:bg-signal-500/40 active:bg-signal-500/80 transition-colors z-20"
              />
              <ChatBotPanel />
            </motion.div>
          </div>

          {/* Right Panel */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 120 }}
            style={{ width: rightWidth }}
            className="relative shrink-0 border-l border-white/5 bg-void-900/40 backdrop-blur-md flex flex-col h-full z-10 p-3"
          >
            <RightPanel />
            {/* Left border resize handle */}
            <div
              onMouseDown={handleRightResize}
              className="absolute top-0 left-0 w-1 h-full cursor-col-resize hover:bg-signal-500/40 active:bg-signal-500/80 transition-colors z-20"
            />
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

          {/* Skills Panel Overlay (Fullscreen) */}
          <AnimatePresence>
            {showSkillsPanel && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="absolute inset-0 max-w-5xl mx-auto pointer-events-none"
              >
                <SkillsOverlay />
              </motion.div>
            )}
          </AnimatePresence>

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
