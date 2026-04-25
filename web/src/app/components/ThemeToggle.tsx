import { FeatherIcon } from '@/icons/feather';

interface ThemeToggleProps {
  theme: 'light' | 'dark';
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--button-border)] bg-[var(--button-bg)] p-0 hover:opacity-80 transition-opacity"
      aria-label="Переключить тему"
    >
      {theme === 'light' ? (
        <FeatherIcon name="moon" size={20} className="text-[var(--foreground)]" />
      ) : (
        <FeatherIcon name="sun" size={20} className="text-[var(--foreground)]" />
      )}
    </button>
  );
}
