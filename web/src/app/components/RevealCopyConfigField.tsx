import { FeatherIcon } from '@/icons/feather';
import { useEffect, useState } from 'react';
import { useCopyNotify } from './CopyToastProvider';

const FIELD_MIN_H = 'min-h-[2.75rem]';
const ACTIONS_MIN_H = 'min-h-[calc(2.75rem*1.2)]';
const SQUARE_BTN = `inline-flex shrink-0 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/40 disabled:opacity-40 transition-colors size-[calc(2.75rem*1.2-0.5rem)]`;

type RevealCopyConfigFieldProps = {
  value: string;
  className?: string;
};

function resetPrivacyState(
  setRevealed: (v: boolean) => void,
  setCopyState: (v: 'idle' | 'copied') => void,
) {
  setRevealed(false);
  setCopyState('idle');
}

export function RevealCopyConfigField({ value, className = '' }: RevealCopyConfigFieldProps) {
  const notifyCopied = useCopyNotify();
  const [revealed, setRevealed] = useState(false);
  const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle');

  useEffect(() => {
    if (copyState !== 'copied') return;
    const t = window.setTimeout(() => {
      setCopyState('idle');
      setRevealed(false);
    }, 10000);
    return () => clearTimeout(t);
  }, [copyState]);

  useEffect(() => {
    const onVisibility = () => {
      resetPrivacyState(setRevealed, setCopyState);
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, []);

  async function copy() {
    if (!value || !revealed) return;
    try {
      await navigator.clipboard.writeText(value);
      notifyCopied();
      setCopyState('copied');
    } catch {
      /* ignore */
    }
  }

  return (
    <div className={`space-y-1.5 ${className}`}>
      <span className="block text-sm text-[var(--muted-foreground)]">Ссылка конфигурации</span>
      <div className="flex rounded-lg border border-[var(--border)] overflow-hidden bg-[var(--input-background)]">
        <div
          className={`flex-1 ${FIELD_MIN_H} flex items-center px-3 py-2 text-sm font-mono break-all whitespace-pre-wrap text-[var(--foreground)] outline-none select-text ${
            revealed ? '' : 'select-none blur-sm'
          }`}
        >
          {value || '—'}
        </div>
        <div
          className={`flex shrink-0 items-center gap-1 border-l border-[var(--border)] bg-[var(--accordion-bg)] px-1 ${ACTIONS_MIN_H}`}
        >
          {!revealed ? (
            <button
              type="button"
              onClick={() => setRevealed(true)}
              className={SQUARE_BTN}
              aria-label="Показать"
            >
              <FeatherIcon name="eye" size={16} className="text-[var(--foreground)]" />
            </button>
          ) : copyState === 'copied' ? (
            <span className={`${SQUARE_BTN} pointer-events-none`} aria-hidden>
              <FeatherIcon name="check" size={16} className="text-green-600" />
            </span>
          ) : (
            <button
              type="button"
              onClick={() => void copy()}
              className={SQUARE_BTN}
              aria-label="Копировать"
            >
              <FeatherIcon name="copy" size={16} className="text-[var(--foreground)]" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
