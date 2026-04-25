import { useState } from 'react';
import { toast } from 'sonner';
import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';
import { Logo } from './Logo';
import { Checkbox } from './ui/checkbox';
import { fetchMe, setToken, verifyGuestCode, type Me } from '@/lib/api';

interface GuestStep2Props {
  email: string;
  onBack: () => void;
  onLogin: (me: Me) => void;
}

export function GuestStep2({ email, onBack, onLogin }: GuestStep2Props) {
  const [code, setCode] = useState('');
  const [rememberDevice, setRememberDevice] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    try {
      const token = await verifyGuestCode(email, code.trim());
      setToken(token, rememberDevice);
      const user = await fetchMe();
      onLogin(user);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Неверный код');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full flex flex-col p-4">
      <div className="shrink-0 pt-4 flex justify-center">
        <Logo variant="auth" />
      </div>
      <div className="flex-1 flex flex-col justify-center py-8">
        <div className="w-full max-w-md mx-auto space-y-8">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
          >
            <FeatherIcon name="arrow-left" size={16} />
            <span className="text-sm">Назад</span>
          </button>

          <div className="text-center">
            <h1 className="mb-2">Проверка кода</h1>
            <p className="text-[var(--muted-foreground)]">
              Введите код из письма, отправленного на {email}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="code" className="block text-sm">
                Код из письма
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]">
                  <FeatherIcon name="key" size={20} />
                </span>
                <input
                  id="code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="000000"
                  className="w-full pl-10 pr-4 py-3 bg-[var(--input-background)] border border-[var(--border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--ring)] font-mono tracking-wider"
                  required
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="remember-device"
                checked={rememberDevice}
                onCheckedChange={(v) => setRememberDevice(v === true)}
              />
              <label
                htmlFor="remember-device"
                className="text-sm text-[var(--muted-foreground)] cursor-pointer select-none transition-colors duration-200 hover:text-[var(--foreground)]"
              >
                Запомнить это устройство
              </label>
            </div>

            <AppPrimaryButton type="submit" disabled={loading} className="w-full">
              {loading ? 'Проверка…' : 'Войти'}
            </AppPrimaryButton>
          </form>
        </div>
      </div>
    </div>
  );
}
