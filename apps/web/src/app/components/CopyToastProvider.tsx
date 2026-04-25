import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';

type CopyToastContextValue = {
  /** Уведомление об успешном копировании (только viewport ≥ lg). */
  notifyCopied: () => void;
};

const CopyToastContext = createContext<CopyToastContextValue | null>(null);

function isLargeViewport(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(min-width: 1024px)').matches;
}

export function CopyToastProvider({ children }: { children: ReactNode }) {
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const notifyCopied = useCallback(() => {
    if (!isLargeViewport()) return;

    clearTimers();
    setExiting(false);
    setVisible(true);

    const t1 = window.setTimeout(() => setExiting(true), 3000);
    const t2 = window.setTimeout(() => {
      setVisible(false);
      setExiting(false);
      clearTimers();
    }, 5000);
    timersRef.current = [t1, t2];
  }, [clearTimers]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  return (
    <CopyToastContext.Provider value={{ notifyCopied }}>
      {children}
      {visible ? (
        <div
          role="status"
          aria-live="polite"
          className={`fixed top-4 left-4 z-[9999] max-w-sm rounded-lg border border-[var(--border)] bg-[var(--accordion-bg)] px-4 py-3 text-sm text-[var(--foreground)] shadow-lg transition-all duration-[2000ms] ease-out ${
            exiting ? 'pointer-events-none opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'
          }`}
        >
          Текст скопирован в буфер обмена
        </div>
      ) : null}
    </CopyToastContext.Provider>
  );
}

export function useCopyNotify(): () => void {
  const ctx = useContext(CopyToastContext);
  if (!ctx) {
    return () => {
      /* no provider */
    };
  }
  return ctx.notifyCopied;
}
