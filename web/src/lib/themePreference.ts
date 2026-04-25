/** Тема из системных настроек ОС/браузера. */
export function getSystemColorScheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function storageKey(email: string): string {
  return `iter_theme_${email.trim().toLowerCase()}`;
}

/** Сохранённая тема для авторизованного пользователя (только явный выбор). */
export function readSavedThemeForEmail(email: string): 'light' | 'dark' | null {
  const v = localStorage.getItem(storageKey(email));
  if (v === 'light' || v === 'dark') return v;
  return null;
}

export function writeSavedThemeForEmail(email: string, theme: 'light' | 'dark'): void {
  localStorage.setItem(storageKey(email), theme);
}
