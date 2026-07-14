import { useRef, useEffect } from "react";
import { Send, Sparkles, ChevronRight, Brain, X } from "lucide-react";
import { useNavigation } from "@/hooks/useNavigation";
import { clsx } from "@/utils/clsx";

export function ChatBotPanel() {
  const {
    messages,
    input,
    setInput,
    isStreaming,
    agentSteps,
    activeStep,
    submitMessage,
    selectedMessageId,
    setSelectedMessageId,
    setMissionControlOpen,
    jumpTo,
    spaceGraph
  } = useNavigation();

  const chatEndRef = useRef<HTMLDivElement>(null);
  
  const rootId = spaceGraph.find((o) => o.parentId === null)?.id ?? "galaxy-root";

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, agentSteps]);

  // Set the selected message to the latest assistant message automatically
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
    <div className="w-full h-full flex flex-col overflow-hidden bg-void-950/40 rounded-xl border border-white/5 shadow-2xl relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5 shrink-0 bg-void-950/60 select-none">
        <div className="flex items-center gap-2">
          <Brain className="h-4.5 w-4.5 text-signal-400 animate-pulse-slow" />
          <div>
            <h2 className="font-display font-semibold text-xs tracking-wide text-mist-100">Mission Control Chat</h2>
            <p className="text-[9px] font-mono text-mist-500 uppercase tracking-widest">Autonomous RAG Agent Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {isStreaming && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-signal-500/20 bg-signal-500/5">
              <span className="h-1.5 w-1.5 rounded-full bg-signal-400 animate-ping" />
              <span className="text-[10px] font-mono text-signal-400 italic">Orbiting...</span>
            </div>
          )}
          
          <button
            onClick={() => {
              setMissionControlOpen(false);
              jumpTo(rootId);
            }}
            className="rounded-md p-1 text-mist-400 hover:bg-white/5 hover:text-mist-100 transition-colors cursor-pointer"
            title="Close Dashboard"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Chat Viewport */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-4 max-w-sm mx-auto space-y-2 select-none">
            <div className="rounded-full bg-signal-500/5 p-3 border border-signal-500/10">
              <Sparkles className="h-6 w-6 text-signal-400/80" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-mist-200 text-xs">Ask RepoVerse AI</h3>
              <p className="text-[11px] text-mist-500 mt-0.5 leading-relaxed">
                Ask any question about the codebase files, dependencies, folder structure, or runtime commands.
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
                  "flex flex-col gap-1 max-w-[90%] rounded-xl px-3 py-2 text-xs transition-all duration-200 cursor-pointer",
                  isUser
                    ? "ml-auto bg-signal-500/10 border border-signal-500/20 text-mist-100 rounded-tr-sm"
                    : clsx(
                        "mr-auto bg-void-800/40 border text-mist-300 rounded-tl-sm",
                        isSelected ? "border-signal-500/30 shadow-md shadow-signal-500/5" : "border-white/5 hover:border-white/10"
                      )
                )}
              >
                {/* Speaker Name */}
                <div className="flex items-center justify-between gap-4 select-none">
                  <span className="text-[9px] uppercase tracking-wider font-semibold text-mist-500">
                    {isUser ? "Navigator" : "RepoVerse AI"}
                  </span>
                  {!isUser && msg.confidence !== undefined && (
                    <span className="text-[8px] font-mono text-emerald-400 bg-emerald-500/10 px-1 py-0.2 rounded border border-emerald-500/15">
                      Confidence: {Math.round(msg.confidence * 100)}%
                    </span>
                  )}
                </div>

                {/* Message Text */}
                <div className="leading-relaxed whitespace-pre-wrap font-body text-mist-200 select-text select-all">
                  {msg.text}
                </div>

                {/* Expandable Agent Decision Tree */}
                {!isUser && msg.steps && msg.steps.length > 0 && (
                  <div className="mt-1.5 pt-1.5 border-t border-white/5 space-y-1">
                    <span className="text-[8px] font-mono text-mist-500 uppercase">Agent Operations:</span>
                    <div className="max-h-20 overflow-y-auto space-y-0.5 pr-1 font-mono text-[9px] text-mist-400">
                      {msg.steps.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-1">
                          <ChevronRight className="h-2.5 w-2.5 text-signal-500 mt-0.5 shrink-0" />
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
          <div className="flex flex-col gap-1 mr-auto max-w-[90%] rounded-xl bg-void-800/30 border border-white/5 px-3 py-2 text-xs">
            <span className="text-[9px] uppercase tracking-wider font-semibold text-mist-500">
              RepoVerse AI
            </span>
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-signal-400 animate-ping" />
              <span className="text-[11px] text-mist-400 italic">Analyzing codebase planets…</span>
            </div>

            {activeStep && (
              <div className="flex items-start gap-1 rounded bg-void-950/40 p-1.5 text-[9px] font-mono text-signal-400 border border-signal-500/10 mt-1 select-none">
                <Sparkles className="h-3 w-3 text-signal-400 animate-pulse shrink-0 mt-0.5" />
                <span>{activeStep}</span>
              </div>
            )}
          </div>
        )}
        
        <div ref={chatEndRef} />
      </div>

      {/* Form Input Area */}
      <div className="p-2 border-t border-white/5 bg-void-950/60 shrink-0 select-none">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitMessage();
          }}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-void-900/40 px-2.5 py-1.5 focus-within:border-signal-500/40 transition-colors"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isStreaming ? "Analyzing..." : "Ask about folders, files, symbols, or run testing commands..."}
            disabled={isStreaming}
            className="flex-1 bg-transparent text-xs text-mist-100 placeholder:text-mist-500 outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="rounded-md p-1 text-signal-400 hover:bg-white/5 hover:text-signal-300 disabled:opacity-30 transition-colors cursor-pointer"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
