import { createContext, useContext, useState, useCallback, useMemo, createElement, type ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import { wsUrl } from "@/lib/api";

/**
 * PHASE 12 — AI CHAT MUST NOT FREEZE THE UNIVERSE.
 *
 * Chat/streaming state lives in its OWN context, fully separated from the
 * navigation/universe context. WebSocket frames update only this context,
 * so per-token setState calls never re-render SpaceScene or any 3D body.
 */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  steps?: string[];
  citations?: any[];
  confidence?: number;
  trace?: string[];
  goal?: any;
  tasks?: any;
  reflection?: any;
  isStreaming?: boolean;
}

interface ChatContextValue {
  messages: ChatMessage[];
  input: string;
  setInput: (v: string) => void;
  isStreaming: boolean;
  agentSteps: string[];
  activeStep: string;
  submitMessage: () => Promise<void>;
  selectedMessageId: string | null;
  setSelectedMessageId: (id: string | null) => void;
  clearChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const { getAccessToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentSteps, setAgentSteps] = useState<string[]>([]);
  const [activeStep, setActiveStep] = useState("");
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  const clearChat = useCallback(() => {
    setMessages([]);
    setAgentSteps([]);
    setActiveStep("");
    setIsStreaming(false);
    setSelectedMessageId(null);
  }, []);

  const submitMessage = useCallback(async () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    const query = input;
    setInput("");
    setAgentSteps([]);
    setIsStreaming(true);

    const token = await getAccessToken();
    const ws = new WebSocket(wsUrl(`/ws/chat`, token));
    const assistantId = `a-${Date.now()}`;
    setSelectedMessageId(assistantId);

    ws.onopen = () => ws.send(query);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "step") {
        setActiveStep(msg.content);
        setAgentSteps((prev) => [...prev, msg.content]);
      } else if (msg.type === "response") {
        setMessages((prev) => {
          const exists = prev.some((m) => m.id === assistantId);
          if (!exists) {
            return [...prev, { id: assistantId, role: "assistant", text: msg.content, isStreaming: true }];
          }
          return prev.map((m) => (m.id === assistantId ? { ...m, text: msg.content } : m));
        });
      } else if (msg.type === "citations") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, citations: msg.content } : m))
        );
      } else if (msg.type === "confidence") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, confidence: msg.content } : m))
        );
      } else if (msg.type === "reasoning_trace") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, trace: msg.content } : m))
        );
      } else if (msg.type === "goal_metadata") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, goal: msg.content } : m))
        );
      } else if (msg.type === "tasks_metadata") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, tasks: msg.content } : m))
        );
      } else if (msg.type === "reflection_status") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, reflection: msg.content } : m))
        );
      } else if (msg.type === "done") {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
        );
        setIsStreaming(false);
        setActiveStep("");
        ws.close();
      } else if (msg.type === "error") {
        setMessages((prev) => [
          ...prev,
          { id: `err-${Date.now()}`, role: "assistant", text: `⚠️ ${msg.content}` },
        ]);
        setIsStreaming(false);
        setActiveStep("");
        ws.close();
      }
    };

    ws.onclose = () => { setIsStreaming(false); setActiveStep(""); };
    ws.onerror = () => {
      setMessages((prev) => [
        ...prev,
        { id: `wserr-${Date.now()}`, role: "assistant", text: "⚠️ Could not reach the AI service. Is the backend running?" },
      ]);
      setIsStreaming(false);
      setActiveStep("");
    };
  }, [input, isStreaming, getAccessToken]);

  const value = useMemo(
    () => ({
      messages, input, setInput, isStreaming, agentSteps, activeStep,
      submitMessage, selectedMessageId, setSelectedMessageId, clearChat,
    }),
    [messages, input, isStreaming, agentSteps, activeStep, submitMessage, selectedMessageId, clearChat]
  );

  return createElement(ChatContext.Provider, { value }, children);
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within a ChatProvider");
  return ctx;
}
