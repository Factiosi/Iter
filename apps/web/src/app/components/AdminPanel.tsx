import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { FeatherIcon } from '@/icons/feather';
import { AppPrimaryButton } from './AppPrimaryButton';
import { Checkbox } from './ui/checkbox';
import {
  addWhitelistEmail,
  fetchMasterSubscription,
  fetchWhitelist,
  patchMasterSubscription,
  patchWhitelistRole,
  removeWhitelistEmail,
  type WhitelistRow,
} from '@/lib/api';
import { roleLabel } from '@/lib/roleLabels';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

/** Роли, доступные для строк whitelist (Dominus только у владельца портала, не из этого списка) */
const WHITELIST_ROLES = ['user', 'moderator'] as const;
const SERVER_NAME_MODES = [
  { value: 'blanc', label: 'Blanc preset' },
  { value: 'liberty', label: 'LIBERTY preset' },
  { value: 'slovo', label: 'Slovo VPN preset' },
  { value: 'custom', label: 'Свои regex-правила' },
  { value: 'none', label: 'Не менять имена' },
] as const;
const OUTPUT_FORMAT_MODES = [
  { value: 'auto', label: 'Авто по User-Agent' },
  { value: 'force_happ', label: 'Всегда Happ/base64 URI' },
  { value: 'force_flclash', label: 'Всегда FlClash YAML' },
  {
    value: 'force_throne',
    label: 'Всегда Throne (sing-box JSON при LIBERTY, иначе base64)',
  },
] as const;
const BYPASS_RENDER_MODES = [
  { value: 'both', label: 'SOCKS + [chain]' },
  { value: 'socks', label: 'Только SOCKS' },
  { value: 'chain', label: 'Только VLESS [chain]' },
] as const;
const SLOVO_RU_DIRECT_ROUTE_PREFIXES =
  'domain:, full:, geosite:, regexp:, keyword:, suffix:';
type SortKey = 'email' | 'config_fetch_count' | 'role';
type SortDirection = 'asc' | 'desc';

function configFetchCountLabel(count: number | null): string {
  return count == null ? 'Не активен' : String(count);
}

function sortArrow(key: SortKey, sortKey: SortKey, direction: SortDirection): string {
  if (key !== sortKey) return '';
  return direction === 'asc' ? ' ↑' : ' ↓';
}

export function AdminPanel() {
  const [rows, setRows] = useState<WhitelistRow[]>([]);
  const [newEmail, setNewEmail] = useState('');
  const [loading, setLoading] = useState(true);
  const [savingEmail, setSavingEmail] = useState<string | null>(null);
  const [masterDraft, setMasterDraft] = useState('');
  const [masterSaved, setMasterSaved] = useState<string | null>(null);
  const [serverNameMode, setServerNameMode] = useState('blanc');
  const [serverNameRules, setServerNameRules] = useState('');
  const [outputFormatMode, setOutputFormatMode] = useState('auto');
  const [bypassRenderMode, setBypassRenderMode] = useState('both');
  const [slovoRuDirectOverride, setSlovoRuDirectOverride] = useState(false);
  const [slovoRuDirectRoutes, setSlovoRuDirectRoutes] = useState('');
  const [slovoRuDirectProviderPreview, setSlovoRuDirectProviderPreview] = useState('');
  const [masterLoading, setMasterLoading] = useState(true);
  const [masterSaving, setMasterSaving] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('email');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const sortedRows = useMemo(() => {
    const dir = sortDirection === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      if (sortKey === 'config_fetch_count') {
        const av = a.config_fetch_count ?? -1;
        const bv = b.config_fetch_count ?? -1;
        if (av !== bv) return (av - bv) * dir;
      } else if (sortKey === 'role') {
        const cmp = roleLabel(a.role).localeCompare(roleLabel(b.role), 'ru');
        if (cmp !== 0) return cmp * dir;
      } else {
        const cmp = a.email.localeCompare(b.email, 'ru');
        if (cmp !== 0) return cmp * dir;
      }
      return a.id - b.id;
    });
  }, [rows, sortDirection, sortKey]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchWhitelist();
      setRows(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось загрузить список');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setMasterLoading(true);
      try {
        const m = await fetchMasterSubscription();
        if (!cancelled) {
          const u = m.master_subscription_url ?? '';
          setMasterSaved(u || null);
          setMasterDraft(u);
          setServerNameMode(m.server_name_mode || 'blanc');
          setServerNameRules(m.server_name_rules || '');
          setOutputFormatMode(m.output_format_mode || 'auto');
          setBypassRenderMode(m.bypass_render_mode || 'socks');
          setSlovoRuDirectOverride(Boolean(m.slovo_ru_direct_override));
          setSlovoRuDirectRoutes(m.slovo_ru_direct_routes || '');
          setSlovoRuDirectProviderPreview(m.slovo_ru_direct_provider_preview || '');
        }
      } catch (err) {
        if (!cancelled) {
          toast.error(err instanceof Error ? err.message : 'Не удалось загрузить мастер-ссылку');
        }
      } finally {
        if (!cancelled) setMasterLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSaveMaster = async () => {
    const url = masterDraft.trim();
    if (!url) {
      toast.error('Введите URL');
      return;
    }
    setMasterSaving(true);
    try {
      const m = await patchMasterSubscription(url, {
        server_name_mode: serverNameMode,
        server_name_rules: serverNameRules,
        output_format_mode: outputFormatMode,
        bypass_render_mode: bypassRenderMode,
        slovo_ru_direct_override: slovoRuDirectOverride,
        slovo_ru_direct_routes: slovoRuDirectRoutes,
      });
      const u = m.master_subscription_url ?? '';
      setMasterSaved(u || null);
      setMasterDraft(u);
      setServerNameMode(m.server_name_mode || 'blanc');
      setServerNameRules(m.server_name_rules || '');
      setOutputFormatMode(m.output_format_mode || 'auto');
      setBypassRenderMode(m.bypass_render_mode || 'socks');
      setSlovoRuDirectOverride(Boolean(m.slovo_ru_direct_override));
      setSlovoRuDirectRoutes(m.slovo_ru_direct_routes || '');
      setSlovoRuDirectProviderPreview(m.slovo_ru_direct_provider_preview || '');
      toast.success('Мастер-ссылка сохранена');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось сохранить');
    } finally {
      setMasterSaving(false);
    }
  };

  const handleAddEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    const em = newEmail.trim();
    if (!em) return;
    try {
      const row = await addWhitelistEmail(em);
      setRows((prev) => [...prev, row].sort((a, b) => a.id - b.id));
      setNewEmail('');
      toast.success('Добавлено');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось добавить');
    }
  };

  const handleRemoveEmail = async (email: string) => {
    try {
      await removeWhitelistEmail(email);
      setRows((prev) => prev.filter((r) => r.email !== email));
      toast.success('Удалено');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось удалить');
    }
  };

  const handleRoleChange = async (email: string, role: string) => {
    setSavingEmail(email);
    try {
      const updated = await patchWhitelistRole(email, role);
      setRows((prev) => prev.map((r) => (r.email === email ? updated : r)));
      toast.success('Роль обновлена');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось сменить роль');
    } finally {
      setSavingEmail(null);
    }
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  return (
    <div className="h-full p-6 lg:p-8">
      <div className="max-w-content mx-auto space-y-6">
        <h1>Администрирование</h1>

        <div className="p-4 lg:p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)] space-y-4">
          <h2 className="text-lg font-semibold">Мастер-ссылка подписки</h2>
          <p className="text-sm text-[var(--muted-foreground)]">
            Единый источник VLESS/Clash для всех пользователей. Изменения не применяются, пока вы не
            нажмёте «Сохранить».
          </p>
          {masterLoading ? (
            <p className="text-sm text-[var(--muted-foreground)]">Загрузка…</p>
          ) : (
            <>
              {masterSaved ? (
                <p className="text-xs font-mono break-all text-[var(--muted-foreground)]">
                  Текущая: {masterSaved}
                </p>
              ) : (
                <p className="text-sm text-amber-700 dark:text-amber-400">
                  Не задана — публичная выдача подписки вернёт ошибку.
                </p>
              )}
              <input
                type="url"
                value={masterDraft}
                onChange={(e) => setMasterDraft(e.target.value)}
                placeholder="https://…"
                className="w-full px-4 py-2 bg-[var(--input-background)] border border-[var(--border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--ring)] font-mono text-sm"
              />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <label className="space-y-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                    Имена серверов
                  </span>
                  <Select value={serverNameMode} onValueChange={setServerNameMode}>
                    <SelectTrigger className="h-10 rounded-lg border-[var(--border)] bg-[var(--input-background)] text-[var(--foreground)] shadow-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]/40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-lg border-[var(--border)] bg-[var(--popover)] text-[var(--popover-foreground)]">
                      {SERVER_NAME_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                    Формат выдачи
                  </span>
                  <Select value={outputFormatMode} onValueChange={setOutputFormatMode}>
                    <SelectTrigger className="h-10 rounded-lg border-[var(--border)] bg-[var(--input-background)] text-[var(--foreground)] shadow-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]/40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-lg border-[var(--border)] bg-[var(--popover)] text-[var(--popover-foreground)]">
                      {OUTPUT_FORMAT_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                    Bypass для nonHapp
                  </span>
                  <Select value={bypassRenderMode} onValueChange={setBypassRenderMode}>
                    <SelectTrigger className="h-10 rounded-lg border-[var(--border)] bg-[var(--input-background)] text-[var(--foreground)] shadow-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]/40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="rounded-lg border-[var(--border)] bg-[var(--popover)] text-[var(--popover-foreground)]">
                      {BYPASS_RENDER_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
              </div>
              {serverNameMode === 'custom' && (
                <label className="block space-y-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                    Regex-правила переименования
                  </span>
                  <textarea
                    value={serverNameRules}
                    onChange={(e) => setServerNameRules(e.target.value)}
                    rows={5}
                    spellCheck={false}
                    placeholder={'^🇩🇪.* => 🇩🇪 Германия\n^(.+?) → Blanc VPN$ => $1'}
                    className="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--input-background)] px-4 py-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                  />
                  <span className="block text-xs leading-relaxed text-[var(--muted-foreground)]">
                    Формат: один regex на строку, затем `=&gt;`, затем новое имя. Пример:
                    `^(.+?) → Blanc VPN$ =&gt; $1`. Если правило не совпало, имя остаётся как в мастер-ссылке.
                  </span>
                </label>
              )}
              {serverNameMode === 'slovo' && (
                <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--input-background)]/40 p-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-medium">Happ: direct-маршруты [RU Direct]</h3>
                    <p className="text-xs leading-relaxed text-[var(--muted-foreground)]">
                      Список правил для профилей «RU сайты работают». Без замены — как у провайдера.
                      С включённой заменой список полностью подменяет провайдера: добавленное попадёт
                      пользователям, удалённое исчезнет даже если было у Slovo.
                    </p>
                  </div>
                  <label className="flex cursor-pointer items-start gap-3">
                    <Checkbox
                      checked={slovoRuDirectOverride}
                      onCheckedChange={(checked) => {
                        const enabled = checked === true;
                        setSlovoRuDirectOverride(enabled);
                        if (enabled && !slovoRuDirectRoutes.trim() && slovoRuDirectProviderPreview) {
                          setSlovoRuDirectRoutes(slovoRuDirectProviderPreview);
                        }
                      }}
                      className="mt-0.5"
                    />
                    <span className="text-sm leading-snug">
                      Заменить список direct-доменов провайдера своим
                    </span>
                  </label>
                  <label className="block space-y-2">
                    <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                      {slovoRuDirectOverride ? 'Свой список' : 'Сейчас у провайдера'}
                    </span>
                    <textarea
                      value={
                        slovoRuDirectOverride ? slovoRuDirectRoutes : slovoRuDirectProviderPreview
                      }
                      onChange={(e) => setSlovoRuDirectRoutes(e.target.value)}
                      readOnly={!slovoRuDirectOverride}
                      rows={12}
                      spellCheck={false}
                      placeholder={'domain:2ip.ru\ngeosite:category-ru\nsuffix:.ru'}
                      className="w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--input-background)] px-4 py-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:cursor-default disabled:opacity-90"
                    />
                    <span className="block text-xs leading-relaxed text-[var(--muted-foreground)]">
                      По одному правилу на строку. Префиксы: {SLOVO_RU_DIRECT_ROUTE_PREFIXES}.
                      Пустые строки и строки с # игнорируются.
                    </span>
                    {slovoRuDirectOverride && slovoRuDirectProviderPreview && (
                      <button
                        type="button"
                        className="text-xs text-[var(--primary)] underline-offset-2 hover:underline"
                        onClick={() => setSlovoRuDirectRoutes(slovoRuDirectProviderPreview)}
                      >
                        Скопировать текущий список провайдера
                      </button>
                    )}
                  </label>
                </div>
              )}
              <AppPrimaryButton
                type="button"
                disabled={masterSaving}
                onClick={() => void handleSaveMaster()}
                className="w-full sm:w-auto"
              >
                <FeatherIcon name="check" size={20} className="text-[var(--foreground)]" />
                {masterSaving ? 'Сохранение…' : 'Сохранить'}
              </AppPrimaryButton>
            </>
          )}
        </div>

        <div className="p-4 lg:p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)]">
          <h2 className="mb-4">Добавить email</h2>
          <form onSubmit={handleAddEmail} className="flex flex-col sm:flex-row gap-2">
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="new@example.com"
              className="flex-1 px-4 py-2 bg-[var(--input-background)] border border-[var(--border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <AppPrimaryButton type="submit" className="shrink-0 whitespace-nowrap">
              <FeatherIcon name="plus" size={20} className="text-[var(--foreground)]" />
              <span>Добавить</span>
            </AppPrimaryButton>
          </form>
        </div>

        <div className="p-4 lg:p-6 bg-[var(--accordion-bg)] rounded-lg border border-[var(--border)]">
          <h2 className="mb-4">Разрешённые email ({rows.length})</h2>
          {loading ? (
            <p className="text-[var(--muted-foreground)] text-sm text-center py-8">Загрузка…</p>
          ) : (
            <div className="space-y-2">
              {rows.length === 0 ? (
                <p className="text-[var(--muted-foreground)] text-sm text-center py-8">
                  Нет разрешённых адресов
                </p>
              ) : (
                <>
                  <div className="hidden sm:grid grid-cols-[minmax(0,1fr)_10rem_11rem_2.5rem] items-center gap-2 px-3 text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                    <button
                      type="button"
                      onClick={() => handleSort('email')}
                      className="text-left transition-colors hover:text-[var(--foreground)]"
                    >
                      Email{sortArrow('email', sortKey, sortDirection)}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSort('config_fetch_count')}
                      className="text-left transition-colors hover:text-[var(--foreground)]"
                    >
                      Обновления{sortArrow('config_fetch_count', sortKey, sortDirection)}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSort('role')}
                      className="text-left transition-colors hover:text-[var(--foreground)]"
                    >
                      Роль{sortArrow('role', sortKey, sortDirection)}
                    </button>
                    <span aria-hidden="true" />
                  </div>
                  {sortedRows.map((row) => (
                    <div
                      key={row.id}
                      className="grid gap-3 p-3 bg-[var(--background)] rounded-lg border border-[var(--border)] sm:grid-cols-[minmax(0,1fr)_10rem_11rem_2.5rem] sm:items-center"
                    >
                      <span className="font-mono text-sm break-all min-w-0">{row.email}</span>
                      <div className="text-sm font-medium">
                        {configFetchCountLabel(row.config_fetch_count)}
                      </div>
                      <Select
                        value={row.role}
                        onValueChange={(role) => void handleRoleChange(row.email, role)}
                        disabled={savingEmail === row.email}
                      >
                        <SelectTrigger
                          className="h-10 min-w-[11rem] rounded-lg border-[var(--border)] bg-[var(--input-background)] text-[var(--foreground)] shadow-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]/40"
                          aria-label="Роль"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="rounded-lg border-[var(--border)] bg-[var(--popover)] text-[var(--popover-foreground)]">
                          {WHITELIST_ROLES.map((r) => (
                            <SelectItem
                              key={r}
                              value={r}
                              className="rounded-md focus:bg-[var(--muted)] focus:text-[var(--foreground)]"
                            >
                              {roleLabel(r)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <button
                        type="button"
                        onClick={() => void handleRemoveEmail(row.email)}
                        className="p-2 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors flex-shrink-0 sm:justify-self-end"
                        aria-label="Удалить"
                      >
                        <FeatherIcon name="trash-2" size={16} className="text-red-600" />
                      </button>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
