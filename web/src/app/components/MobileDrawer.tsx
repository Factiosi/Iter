import { useState } from 'react';
import { FeatherIcon, type FeatherIconName } from '@/icons/feather';

interface MobileDrawerProps {
  currentPage: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin';
  onNavigate: (page: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin') => void;
  isAdmin?: boolean;
}

const MAIN_NAV: { id: 'instructions' | 'vpn' | 'profile' | 'admin'; label: string; icon: FeatherIconName }[] = [
  { id: 'instructions', label: 'Инструкции', icon: 'book-open' },
  { id: 'vpn', label: 'Настройки VPN', icon: 'settings' },
  { id: 'profile', label: 'Профиль', icon: 'user' },
];

export function MobileDrawer({ currentPage, onNavigate, isAdmin = false }: MobileDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [...MAIN_NAV];
  if (isAdmin) {
    navItems.push({ id: 'admin', label: 'Администрирование', icon: 'shield' });
  }

  const handleNavigate = (page: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin') => {
    onNavigate(page);
    setIsOpen(false);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 px-6 py-3 bg-[var(--button-bg)] border border-[var(--button-border)] rounded-full shadow-lg hover:opacity-80 transition-opacity flex items-center gap-2"
      >
        <FeatherIcon name="menu" size={20} className="text-[var(--foreground)]" />
        <span className="text-[var(--foreground)]">Меню</span>
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-50"
          onClick={() => setIsOpen(false)}
        />
      )}

      <div
        className={`fixed bottom-0 left-0 right-0 bg-[var(--sidebar)] rounded-t-2xl z-50 transition-transform duration-300 ${
          isOpen ? 'translate-y-0' : 'translate-y-full'
        }`}
      >
        <div className="p-4">
          <button
            onClick={() => setIsOpen(false)}
            className="absolute top-4 right-4 p-2 hover:bg-[var(--sidebar-accent)] rounded-lg transition-colors"
          >
            <FeatherIcon name="x" size={20} className="text-[var(--sidebar-foreground)]" />
          </button>

          <div className="pt-8 pb-4 space-y-2">
            {navItems.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigate(item.id)}
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
          </div>

          <div className="pt-4 border-t border-[var(--sidebar-border)]">
            <button
              onClick={() => handleNavigate('support')}
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
        </div>
      </div>
    </>
  );
}
