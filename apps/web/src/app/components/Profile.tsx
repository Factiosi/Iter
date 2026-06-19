import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';
import { roleLabel } from '@/lib/roleLabels';

interface ProfileProps {
  email: string;
  role: string;
  onLogout: () => void;
}

export function Profile({ email, role, onLogout }: ProfileProps) {
  return (
    <div className="h-full p-6 lg:p-8">
      <div className="max-w-content mx-auto space-y-6">
        <h1>Профиль</h1>

        <div className="space-y-4">
          <div className="p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)]">
            <div className="mb-6">
              <h3 className="mb-1">Ваш аккаунт</h3>
              <p className="text-[var(--muted-foreground)]">{email || '—'}</p>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between py-3 border-b border-[var(--border)]">
                <span className="text-[var(--muted-foreground)]">Статус</span>
                <span className="text-green-600">Активен</span>
              </div>
              <div className="flex justify-between py-3">
                <span className="text-[var(--muted-foreground)]">Права</span>
                <span>{roleLabel(role)}</span>
              </div>
            </div>
          </div>

          <AppPrimaryButton type="button" onClick={onLogout} className="w-full">
            <FeatherIcon name="log-out" size={20} className="text-[var(--foreground)]" />
            <span>Выйти</span>
          </AppPrimaryButton>
        </div>
      </div>
    </div>
  );
}
