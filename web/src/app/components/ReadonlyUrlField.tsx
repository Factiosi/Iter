import { FeatherIcon } from '@/icons/feather';
import { useState } from 'react';
import { useCopyNotify } from './CopyToastProvider';

const FIELD_MIN_H = 'min-h-[2.75rem]';
const ACTIONS_MIN_H = 'min-h-[calc(2.75rem*1.2)]';
const SQUARE_BTN = `inline-flex shrink-0 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]/40 disabled:opacity-40 transition-colors size-[calc(2.75rem*1.2-0.5rem)]`;

type ReadonlyUrlFieldProps = {
  id?: string;
  label: string;
  value: string;
  className?: string;
  showOpen?: boolean;
  showCopy?: boolean;
};

export function ReadonlyUrlField({
  id,
  label,
  value,
  className = '',
  showOpen = true,
  showCopy = true,
}: ReadonlyUrlFieldProps) {
  const notifyCopied = useCopyNotify();
  const [justCopied, setJustCopied] = useState(false);

  async function copy() {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      notifyCopied();
      setJustCopied(true);
      window.setTimeout(() => setJustCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  function openLink() {
    if (!value) return;
    window.open(value, '_blank', 'noopener,noreferrer');
  }

  const hasActions = showOpen || showCopy;

  return (
    <div className={`space-y-1.5 ${className}`}>
      <span id={id ? `${id}-label` : undefined} className="block text-sm text-[var(--muted-foreground)]">
        {label}
      </span>
      <div
        className="flex rounded-lg border border-[var(--border)] overflow-hidden bg-[var(--input-background)]"
        role="group"
        aria-labelledby={id ? `${id}-label` : undefined}
      >
        <div
          className={`flex-1 ${FIELD_MIN_H} flex items-center px-3 py-2 text-sm font-mono text-[var(--foreground)] break-all outline-none select-text`}
        >
          {value || '—'}
        </div>
        {hasActions ? (
          <div
            className={`flex shrink-0 items-center gap-1 border-l border-[var(--border)] bg-[var(--accordion-bg)] px-1 ${ACTIONS_MIN_H}`}
          >
            {showOpen ? (
              <button
                type="button"
                onClick={openLink}
                disabled={!value}
                className={SQUARE_BTN}
                aria-label="Открыть ссылку"
              >
                <FeatherIcon name="external-link" size={16} className="text-[var(--foreground)]" />
              </button>
            ) : null}
            {showCopy ? (
              <button
                type="button"
                onClick={() => void copy()}
                disabled={!value}
                className={SQUARE_BTN}
                aria-label="Копировать"
              >
                {justCopied ? (
                  <FeatherIcon name="check" size={16} className="text-green-600" />
                ) : (
                  <FeatherIcon name="copy" size={16} className="text-[var(--foreground)]" />
                )}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
