import { useState } from 'react';
import { toast } from 'sonner';
import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';
import { Logo } from './Logo';
import { requestGuestCode } from '@/lib/api';

interface GuestStep1Props {
  onNext: (email: string) => void;
}

export function GuestStep1({ onNext }: GuestStep1Props) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try {
      await requestGuestCode(email.trim());
      toast.success('Далее введите код');
      onNext(email.trim());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось продолжить');
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
          <div className="text-center">
            <h1 className="mb-2">Войдите для доступа к порталу</h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm">
                Электронная почта
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]">
                  <FeatherIcon name="mail" size={20} />
                </span>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  autoComplete="email"
                  className="w-full pl-10 pr-4 py-3 bg-[var(--input-background)] border border-[var(--border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  required
                />
              </div>
            </div>

            <AppPrimaryButton type="submit" disabled={loading} className="w-full">
              {loading ? 'Отправка…' : 'Получить код'}
            </AppPrimaryButton>
          </form>
        </div>
      </div>
    </div>
  );
}
