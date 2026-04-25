import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { FeatherIcon } from '@/icons/feather';
import {
  createGuestVpnLink,
  deleteGuestVpnLink,
  fetchGuestVpnLinks,
  fetchMainVpnLinks,
  fetchVpnGenerateLinks,
  type GuestVpnLinkOut,
  type VpnGeneratedLinks,
} from '@/lib/api';
import { AppPrimaryButton } from './AppPrimaryButton';
import { ReadonlyUrlField } from './ReadonlyUrlField';
import { RevealCopyConfigField } from './RevealCopyConfigField';

type VPNSettingsProps = {
  canCreateGuestLinks: boolean;
};

export function VPNSettings({ canCreateGuestLinks }: VPNSettingsProps) {
  const [generated, setGenerated] = useState<VpnGeneratedLinks | null>(null);
  const [mainLoading, setMainLoading] = useState(true);
  const [genLoading, setGenLoading] = useState(false);
  const [guestLinks, setGuestLinks] = useState<GuestVpnLinkOut[]>([]);
  const [guestLoading, setGuestLoading] = useState(false);
  const [guestCreating, setGuestCreating] = useState(false);
  const [guestDeletingSlot, setGuestDeletingSlot] = useState<number | null>(null);

  const loadGuestLinks = useCallback(async () => {
    if (!canCreateGuestLinks) return;
    setGuestLoading(true);
    try {
      const list = await fetchGuestVpnLinks();
      setGuestLinks(list);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось загрузить гостевые ссылки');
    } finally {
      setGuestLoading(false);
    }
  }, [canCreateGuestLinks]);

  useEffect(() => {
    void loadGuestLinks();
  }, [loadGuestLinks]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setMainLoading(true);
      try {
        const data = await fetchMainVpnLinks();
        if (!cancelled) setGenerated(data);
      } catch (err) {
        if (!cancelled) {
          toast.error(err instanceof Error ? err.message : 'Не удалось загрузить ссылки VPN');
        }
      } finally {
        if (!cancelled) setMainLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerate = async () => {
    setGenLoading(true);
    try {
      const data = await fetchVpnGenerateLinks();
      setGenerated(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось сгенерировать ссылки');
    } finally {
      setGenLoading(false);
    }
  };

  const usedSlots = new Set(guestLinks.map((g) => g.slot));
  const nextGuestSlot = [1, 2, 3].find((s) => !usedSlots.has(s)) ?? null;
  const canCreateMoreGuest = canCreateGuestLinks && nextGuestSlot !== null;

  const handleCreateGuest = async () => {
    setGuestCreating(true);
    try {
      const row = await createGuestVpnLink();
      setGuestLinks((prev) => [...prev, row].sort((a, b) => a.slot - b.slot));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось создать гостевую ссылку');
    } finally {
      setGuestCreating(false);
    }
  };

  const handleDeleteGuest = async (slot: number) => {
    setGuestDeletingSlot(slot);
    try {
      await deleteGuestVpnLink(slot);
      setGuestLinks((prev) => prev.filter((g) => g.slot !== slot));
      toast.success('Гостевая ссылка удалена');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось удалить ссылку');
    } finally {
      setGuestDeletingSlot(null);
    }
  };

  return (
    <div className="h-full p-6 lg:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1>Настройки VPN</h1>

        <div className="p-4 lg:p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)] space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-[var(--muted)] rounded-lg flex items-center justify-center flex-shrink-0 text-[var(--muted-foreground)]">
              <FeatherIcon name="link-2" size={20} />
            </div>
            <div className="flex-1 space-y-2">
              <h2 className="text-lg font-semibold">Ссылки VPN</h2>
              <p className="text-sm text-[var(--muted-foreground)]">
                Создание ссылки для добавление подписки в приложения, а так же ссылка конфигурации
                (для продвинутых пользователей)
              </p>
            </div>
          </div>
          {!generated ? (
            <AppPrimaryButton
              type="button"
              disabled={genLoading || mainLoading}
              onClick={() => void handleGenerate()}
              className="w-full"
            >
              <FeatherIcon name="key" size={20} className="text-[var(--foreground)]" />
              {mainLoading || genLoading ? 'Загрузка…' : 'Сгенерировать ссылку'}
            </AppPrimaryButton>
          ) : null}

          {generated ? (
            <div className="space-y-4 pt-2 border-t border-[var(--border)]">
              <ReadonlyUrlField
                id="vpn-subscription-happ"
                label="Deeplink для Happ"
                value={generated.happ_url}
              />
              <ReadonlyUrlField
                id="vpn-subscription-flclash"
                label="Deeplink для FlClash"
                value={generated.flclash_url}
              />
              <RevealCopyConfigField value={generated.config_text} />
            </div>
          ) : null}
        </div>

        {canCreateGuestLinks ? (
          <div className="p-4 lg:p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)] space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-[var(--muted)] rounded-lg flex items-center justify-center flex-shrink-0 text-[var(--muted-foreground)]">
                <FeatherIcon name="link" size={20} />
              </div>
              <div className="flex-1 space-y-2">
                <h2 className="text-lg font-semibold">Гостевые ссылки</h2>
                <p className="text-sm text-[var(--muted-foreground)]">
                  Создание до 3х гостевых ссылок VPN, доступ к которым вы можете в любой момент прервать
                </p>
              </div>
            </div>
            {guestLoading ? (
              <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
            ) : (
              <div className="space-y-4">
                {guestLinks.map((g) => (
                  <div key={g.slot} className="space-y-2">
                    <ReadonlyUrlField
                      id={`guest-${g.slot}-happ`}
                      label="Гостевая ссылка для Happ"
                      value={g.happ_url}
                    />
                    <ReadonlyUrlField
                      id={`guest-${g.slot}-flclash`}
                      label="Гостевая ссылка для FlClash"
                      value={g.flclash_url}
                    />
                    <button
                      type="button"
                      disabled={guestDeletingSlot === g.slot}
                      onClick={() => void handleDeleteGuest(g.slot)}
                      className="w-full py-2.5 text-sm font-medium rounded-lg border border-[var(--border)] bg-[var(--button-bg)] hover:opacity-80 transition-opacity disabled:opacity-50"
                    >
                      {guestDeletingSlot === g.slot ? 'Удаление…' : 'Удалить гостевую ссылку'}
                    </button>
                  </div>
                ))}
                {canCreateMoreGuest ? (
                  <AppPrimaryButton
                    type="button"
                    disabled={guestCreating}
                    onClick={() => void handleCreateGuest()}
                    className="w-full"
                  >
                    <FeatherIcon name="key" size={20} className="text-[var(--foreground)]" />
                    <FeatherIcon name="user-plus" size={20} className="text-[var(--foreground)]" />
                    {guestCreating ? 'Создание…' : `Создать гостевую ссылку ${nextGuestSlot}`}
                  </AppPrimaryButton>
                ) : null}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
