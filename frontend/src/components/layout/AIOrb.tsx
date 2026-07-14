import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, X, ChevronRight, Brain, AlertCircle, FileText, CheckCircle2 } from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";
import { clsx } from "@/utils/clsx";

export function AIOrb() {
  const {
    isMissionControlOpen,
    setMissionControlOpen,
    messages,
    input,
    setInput,
    isStreaming,
    agentSteps,
    activeStep,
    submitMessage,
    selectedMessageId,
    setSelectedMessageId
  } = useNavigation();

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom when streaming or new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, agentSteps]);

  // Set the selected message to the latest assistant message automatically when streaming or done
  useEffect(() => {
    const assistantMsgs = messages.filter(m => m.role === "assistant");
    if (assistantMsgs.length > 0) {
      const latest = assistantMsgs[assistantMsgs.length - 1];
      if (latest.id !== selectedMessageId) {
        setSelectedMessageId(latest.id);
      }
    }
  }, [messages, selectedMessageId, setSelectedMessageId]);

  return (
    <div className="absolute inset-0 pointer-events-none z-30">
      {/* ─── AI ORB (Pulsing Sphere) ─── */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-auto">
        <AnimatePresence>
          {!isMissionControlOpen && (
            <motion.button
              layoutId="ai-orb"
              onClick={() => setMissionControlOpen(true)}
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.95 }}
              className="relative flex items-center justify-center h-16 w-16 rounded-full border border-signal-400/40 bg-void-950/80 shadow-glow backdrop-blur-md cursor-pointer group"
            >
              <div className="absolute inset-0.5 rounded-full bg-gradient-to-tr from-signal-600/20 to-signal-400/40 animate-pulse" />
              <Sparkles className="h-6 w-6 text-signal-400 group-hover:rotate-12 transition-transform duration-300" strokeWidth={1.5} />
              
              {/* Pulsing Outer Rings */}
              <span className="absolute -inset-1 rounded-full border border-signal-400/20 animate-ping opacity-60 pointer-events-none" />
              <span className="absolute -inset-3 rounded-full border border-signal-500/10 animate-pulse-slow pointer-events-none" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* ─── MISSION CONTROL PANEL OVERLAY ─── */}
      <AnimatePresence>
        {isMissionControlOpen && (
          <div className="absolute inset-0 bg-void-950/40 backdrop-blur-sm pointer-events-auto flex items-center justify-center p-6">
            {/* Smooth transition box */}
            <motion.div
              layoutId="ai-orb"
              className="relative w-full max-w-2xl h-[80vh] bg-void-900/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
              transition={{ type: "spring", damping: 25, stiffness: 140 }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 shrink-0 bg-void-950/40">
                <div className="flex items-center gap-2.5">
                  <Brain className="h-5 w-5 text-signal-400 animate-pulse-slow" />
                  <div>
                    <h2 className="font-display font-semibold text-sm tracking-wide text-mist-100">Mission Control</h2>
                    <p className="text-[10px] font-mono text-mist-500 uppercase tracking-widest">Autonomous RAG Agent Engine</p>
                  </div>
                </div>
                
                <button
                  onClick={() => setMissionControlOpen(false)}
                  className="rounded-lg p-2 text-mist-400 hover:bg-white/5 hover:text-mist-100 transition-colors cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Chat Viewport */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 scroll-smooth">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-sm mx-auto space-y-4">
                    <div className="rounded-full bg-signal-500/10 p-4 border border-signal-500/20">
                      <Sparkles className="h-8 w-8 text-signal-400" />
                    </div>
                    <div>
                      <h3 className="font-display font-semibold text-mist-100 text-sm">Ask RepoVerse AI</h3>
                      <p className="text-xs text-mist-500 mt-1 leading-relaxed">
                        I am your spacecraft teacher. Ask me any question about the codebase, files, structures, or logic.
                      </p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.role === "user";
                    const isSelected = msg.id === selectedMessageId;

                    return (
                      <div
                        key={msg.id}
                        onClick={() => !isUser && setSelectedMessageId(msg.id)}
                        className={clsx(
                          "flex flex-col gap-1.5 max-w-[85%] rounded-2xl px-4 py-3 text-sm transition-all duration-200 cursor-pointer",
                          isUser
                            ? "ml-auto bg-signal-500/15 border border-signal-500/30 text-mist-100 rounded-tr-sm"
                            : clsx(
                                "mr-auto bg-void-800/60 border text-mist-300 rounded-tl-sm",
                                isSelected ? "border-signal-500/50 shadow-md shadow-signal-500/5" : "border-white/5 hover:border-white/10"
                              )
                        )}
                      >
                        {/* Speaker Name */}
                        <div className="flex items-center justify-between gap-4 select-none">
                          <span className="text-[10px] uppercase tracking-wider font-semibold text-mist-500">
                            {isUser ? "Navigator" : "RepoVerse AI"}
                          </span>
                          {!isUser && msg.confidence !== undefined && (
                            <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              Confidence: {Math.round(msg.confidence * 100)}%
                            </span>
                          )}
                        </div>

                        {/* Message Text */}
                        <div className="leading-relaxed whitespace-pre-wrap font-body text-mist-200 text-xs">
                          {msg.text}
                        </div>

                        {/* Expandable Agent Decision Tree */}
                        {!isUser && msg.steps && msg.steps.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-white/5 space-y-1">
                            <span className="text-[9px] font-mono text-mist-500 uppercase">Agent Operations:</span>
                            <div className="max-h-24 overflow-y-auto space-y-1 pr-1">
                              {msg.steps.map((step, idx) => (
                                <div key={idx} className="flex items-start gap-1.5 text-[10px] font-mono text-mist-400">
                                  <ChevronRight className="h-3 w-3 text-signal-500 mt-0.5 shrink-0" />
                                  <span>{step}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}

                {/* Agent Steps / Thinking State (Active message) */}
                {isStreaming && (
                  <div className="flex flex-col gap-2 mr-auto max-w-[85%] rounded-2xl bg-void-800/40 border border-white/5 px-4 py-3 text-sm">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-mist-500">
                      RepoVerse AI
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-signal-400 animate-ping" />
                      <span className="text-xs text-mist-400 italic">Analyzing codebase planets…</span>
                    </div>

                    {/* Show current executing step */}
                    {activeStep && (
                      <div className="flex items-start gap-1.5 rounded bg-void-950/50 p-2 text-[10px] font-mono text-signal-400 border border-signal-500/10 mt-1 select-none">
                        <Sparkles className="h-3.5 w-3.5 text-signal-400 animate-pulse shrink-0 mt-0.5" />
                        <span>{activeStep}</span>
                      </div>
                    )}
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>

              {/* Form Input Area */}
              <div className="p-4 border-t border-white/5 bg-void-950/40 shrink-0">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitMessage();
                  }}
                  className="flex items-center gap-2 rounded-lg border border-white/10 bg-void-900/80 px-3 py-2 focus-within:border-signal-500/50 transition-colors"
                >
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={isStreaming ? "Analyzing..." : "Ask your teacher about files, functions, or structures..."}
                    disabled={isStreaming}
                    className="flex-1 bg-transparent text-xs text-mist-100 placeholder:text-mist-500 outline-none disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || isStreaming}
                    className="rounded-md p-1.5 text-signal-400 hover:bg-white/5 hover:text-signal-300 disabled:opacity-30 transition-colors cursor-pointer"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
