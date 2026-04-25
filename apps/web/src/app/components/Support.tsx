import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';

const SUPPORT_EMAIL = 'help@factiosi.com';
const TELEGRAM_URL = 'https://t.me/factiosi';

export function Support() {
  return (
    <div className="h-full p-6 lg:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1>Поддержка</h1>

        <div className="space-y-4">
          <div className="p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)]">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[var(--muted)] rounded flex items-center justify-center flex-shrink-0">
                <FeatherIcon name="mail" size={24} className="text-[var(--muted-foreground)]" />
              </div>
              <div className="flex-1">
                <h3 className="mb-2">Email поддержки</h3>
                <p className="text-[var(--muted-foreground)] mb-4">
                  Напишите нам на {SUPPORT_EMAIL} — мы ответим как можно скорее.
                </p>
                <AppPrimaryButton asChild className="w-full sm:w-auto">
                  <a href={`mailto:${SUPPORT_EMAIL}`}>Написать письмо</a>
                </AppPrimaryButton>
              </div>
            </div>
          </div>

          <div className="p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)]">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[var(--muted)] rounded flex items-center justify-center flex-shrink-0">
                <FeatherIcon name="send" size={24} className="text-[var(--muted-foreground)]" />
              </div>
              <div className="flex-1">
                <h3 className="mb-2">Telegram-чат</h3>
                <p className="text-[var(--muted-foreground)] mb-4">Связаться с Factiosi в Telegram</p>
                <AppPrimaryButton asChild className="w-full sm:w-auto">
                  <a href={TELEGRAM_URL} target="_blank" rel="noopener noreferrer">
                    Перейти к диалогу
                  </a>
                </AppPrimaryButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
