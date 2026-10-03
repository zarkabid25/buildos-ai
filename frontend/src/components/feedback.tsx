"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Toasts (BUILD-118) and confirmation dialogs (BUILD-119) in one small provider,
// so pages don't need a UI library or window.alert/confirm.

type ToastKind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ConfirmOptions {
  title: string;
  body?: string;
  confirmLabel?: string;
  danger?: boolean;
}

interface FeedbackContextValue {
  toast: (text: string, kind?: ToastKind) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const FeedbackContext = createContext<FeedbackContextValue | undefined>(undefined);

const TOAST_CLASSES: Record<ToastKind, string> = {
  success: "border-success/40 text-success",
  error: "border-danger/40 text-danger",
  info: "border-border text-ink",
};

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [pending, setPending] = useState<(ConfirmOptions & { resolve: (ok: boolean) => void }) | null>(null);
  const nextId = useRef(0);

  const toast = useCallback((text: string, kind: ToastKind = "info") => {
    const id = ++nextId.current;
    // Keep at most three on screen; errors stay a little longer than confirmations.
    setToasts((prev) => [...prev.slice(-2), { id, kind, text }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), kind === "error" ? 7000 : 4000);
  }, []);

  const confirm = useCallback(
    (options: ConfirmOptions) => new Promise<boolean>((resolve) => setPending({ ...options, resolve })),
    []
  );

  function close(ok: boolean) {
    pending?.resolve(ok);
    setPending(null);
  }

  return (
    <FeedbackContext.Provider value={{ toast, confirm }}>
      {children}

      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.kind === "error" ? "alert" : "status"}
            className={cn("pointer-events-auto rounded-md border bg-surface px-4 py-3 text-sm shadow-sm", TOAST_CLASSES[t.kind])}
          >
            <div className="flex items-start justify-between gap-3">
              <span>{t.text}</span>
              <button
                aria-label="Dismiss"
                className="text-muted hover:text-ink"
                onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>

      {pending && <ConfirmDialog options={pending} onClose={close} />}
    </FeedbackContext.Provider>
  );
}

function ConfirmDialog({ options, onClose }: { options: ConfirmOptions; onClose: (ok: boolean) => void }) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Focus the safe choice, and let Escape cancel.
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={() => onClose(false)}>
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-sm rounded-card border border-border bg-surface p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-title" className="text-base font-semibold text-ink">
          {options.title}
        </h2>
        {options.body && <p className="mt-2 text-sm text-muted">{options.body}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <Button ref={cancelRef} variant="secondary" onClick={() => onClose(false)}>
            Cancel
          </Button>
          <Button variant={options.danger ? "danger" : "primary"} onClick={() => onClose(true)}>
            {options.confirmLabel ?? "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function useFeedback() {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback must be used within FeedbackProvider");
  return ctx;
}
