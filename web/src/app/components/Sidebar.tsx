import { FeatherIcon, type FeatherIconName } from '@/icons/feather';
import { Logo } from './Logo';

interface SidebarProps {
  currentPage: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin';
  onNavigate: (page: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin') => void;
  isAdmin?: boolean;
}

const MAIN_NAV: { id: 'instructions' | 'vpn' | 'profile' | 'admin'; label: string; icon: FeatherIconName }[] = [
  { id: 'instructions', label: 'Инструкции', icon: 'book-open' },
  { id: 'vpn', label: 'Настройки VPN', icon: 'settings' },
  { id: 'profile', label: 'Профиль', icon: 'user' },
];

export function Sidebar({ currentPage, onNavigate, isAdmin = false }: SidebarProps) {
  const navItems = [...MAIN_NAV];
  if (isAdmin) {
    navItems.push({ id: 'admin', label: 'Администрирование', icon: 'shield' });
  }

  return (
    <aside className="w-64 h-screen bg-[var(--sidebar)] border-r border-[var(--sidebar-border)] flex flex-col">
      <div className="flex w-full items-center justify-center pt-4 pb-2">
        <Logo />
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-[var(--sidebar-accent)] text-[var(--sidebar-accent-foreground)]'
                  : 'text-[var(--sidebar-foreground)] hover:bg-[var(--sidebar-accent)]/50'
              }`}
            >
              <FeatherIcon name={item.icon} size={20} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[var(--sidebar-border)]">
        <button
          onClick={() => onNavigate('support')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
            currentPage === 'support'
              ? 'bg-[var(--sidebar-accent)] text-[var(--sidebar-accent-foreground)]'
              : 'text-[var(--sidebar-foreground)] hover:bg-[var(--sidebar-accent)]/50'
          }`}
        >
          <FeatherIcon name="help-circle" size={20} />
          <span>Поддержка</span>
        </button>
      </div>
    </aside>
  );
}
