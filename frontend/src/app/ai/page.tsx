"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { InsightsList, RulesNote } from "@/components/insights-list";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  useAiStatus,
  useChat,
  useDecideProposal,
  useInsights,
  useProposals,
  type ToolCall,
} from "@/lib/use-ai";

const SUGGESTIONS = [
  "Which projects are at risk?",
  "What materials should I order?",
  "Show me delayed projects",
  "Which materials will run out soonest?",
  "Summarize recent site reports",
];

interface ChatLine {
  role: "user" | "assistant" | "error";
  content: string;
  toolCalls?: ToolCall[];
}

export default function AiCommandCenterPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { data: status } = useAiStatus();
  const { data: insights } = useInsights();
  const { data: pending } = useProposals("pending");
  const chat = useChat();
  const decide = useDecideProposal();

  const [input, setInput] = useState("");
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  if (authLoading || !user) return null;

  const configured = status?.configured ?? false;

  async function send(message: string) {
    const text = message.trim();
    if (!text || chat.isPending) return;
    setInput("");
    setLines((prev) => [...prev, { role: "user", content: text }]);
    try {
      const res = await chat.mutateAsync({ message: text, conversation_id: conversationId });
      setConversationId(res.conversation_id);
      setLines((prev) => [...prev, { role: "assistant", content: res.reply, toolCalls: res.tool_calls }]);
    } catch (err) {
      setLines((prev) => [
        ...prev,
        { role: "error", content: err instanceof ApiError ? err.message : "Something went wrong" },
      ]);
    }
  }

  async function handleDecision(id: string, decision: "approve" | "reject") {
    setDecisionError(null);
    try {
      await decide.mutateAsync({ id, decision });
    } catch (err) {
      setDecisionError(err instanceof ApiError ? err.message : "Could not record that decision");
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">AI Command Center</h1>
          <p className="text-muted">Ask about your projects, stock, costs and site activity.</p>
        </div>

        {status && !configured && (
          <Card className="border-warning/50 bg-amber-50/50">
            <div className="text-sm font-medium text-ink">The AI assistant isn&apos;t switched on yet</div>
            <p className="mt-1 text-sm text-muted">
              Chat needs an Anthropic API key. An administrator sets <code>LLM_API_KEY</code> on the server and
              restarts it. Everything else on this page works without it, including the insights below.
            </p>
          </Card>
        )}

        <Card>
          <h2 className="mb-1 text-sm font-semibold text-ink">Needs attention</h2>
          {insights && (
            <>
              <p className="mb-1 text-sm text-ink">{insights.summary}</p>
              <RulesNote />
              <div className="mt-2">
                <InsightsList insights={insights.insights} limit={5} />
              </div>
            </>
          )}
        </Card>

        {pending && pending.length > 0 && (
          <Card className="border-primary/40 bg-blue-50/40">
            <h2 className="mb-1 text-sm font-semibold text-ink">Drafts waiting for your approval</h2>
            <p className="mb-3 text-xs text-muted">
              The assistant only suggests these. Nothing is created until you approve, and quantities are
              estimates you should check first.
            </p>
            <ul className="space-y-3">
              {pending.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-ink">{p.summary}</span>
                  <span className="flex shrink-0 gap-2">
                    <Button onClick={() => handleDecision(p.id, "approve")} disabled={decide.isPending}>
                      Approve
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => handleDecision(p.id, "reject")}
                      disabled={decide.isPending}
                    >
                      Reject
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
            {decisionError && <p className="mt-2 text-sm text-danger">{decisionError}</p>}
          </Card>
        )}

        <Card>
          <div className="min-h-[12rem] space-y-4">
            {lines.length === 0 && (
              <div>
                <p className="mb-3 text-sm text-muted">Try asking:</p>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      disabled={!configured}
                      onClick={() => send(s)}
                      className="rounded-full border border-border px-3 py-1 text-xs text-ink hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {lines.map((line, i) => (
              <div key={i} className={line.role === "user" ? "text-right" : ""}>
                <div
                  className={`inline-block max-w-full whitespace-pre-wrap rounded-md px-3 py-2 text-left text-sm ${
                    line.role === "user"
                      ? "bg-primary text-white"
                      : line.role === "error"
                        ? "bg-red-50 text-danger"
                        : "bg-gray-100 text-ink"
                  }`}
                >
                  {line.content}
                </div>
                {line.toolCalls && line.toolCalls.length > 0 && (
                  <div className="mt-1 text-xs text-muted">
                    Looked up: {Array.from(new Set(line.toolCalls.map((t) => t.name.replace(/_/g, " ")))).join(", ")}
                  </div>
                )}
              </div>
            ))}
            {chat.isPending && <div className="text-sm text-muted">Thinking...</div>}
            <div ref={bottomRef} />
          </div>

          <form
            className="mt-4 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              className="h-10 flex-1 rounded-md border border-border bg-surface px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:bg-gray-50"
              placeholder={configured ? "Ask BuildOS..." : "Chat is unavailable until an API key is set"}
              value={input}
              maxLength={4000}
              disabled={!configured}
              onChange={(e) => setInput(e.target.value)}
            />
            <Button type="submit" disabled={!configured || chat.isPending || !input.trim()}>
              Ask
            </Button>
          </form>
          {configured && (
            <p className="mt-2 text-xs text-muted">
              Answers come from your own data via read-only lookups. Check important figures before acting on them.
            </p>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
