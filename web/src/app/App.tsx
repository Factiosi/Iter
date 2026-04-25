import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { MobileDrawer } from './components/MobileDrawer';
import { GuestStep1 } from './components/GuestStep1';
import { GuestStep2 } from './components/GuestStep2';
import { Instructions } from './components/Instructions';
import { VPNSettings } from './components/VPNSettings';
import { Profile } from './components/Profile';
import { Support } from './components/Support';
import { AdminPanel } from './components/AdminPanel';
import { ThemeToggle } from './components/ThemeToggle';
import { clearToken, fetchMe, getToken, type Me } from '@/lib/api';
import {
  getSystemColorScheme,
  readSavedThemeForEmail,
  writeSavedThemeForEmail,
} from '@/lib/themePreference';

type Screen =
  | 'guest1'
  | 'guest2'
  | 'instructions'
  | 'vpn'
  | 'profile'
  | 'support'
  | 'admin';

export default function App() {
  const [screen, setScreen] = useState<Screen>('guest1');
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    typeof window !== 'undefined' ? getSystemColorScheme() : 'light',
  );
  const [pendingGuestEmail, setPendingGuestEmail] = useState('');
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  useEffect(() => {
    if (!me) {
      setTheme(getSystemColorScheme());
      return;
    }
    const saved = readSavedThemeForEmail(me.email);
    setTheme(saved ?? getSystemColorScheme());
  }, [me]);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      const sys = mq.matches ? 'dark' : 'light';
      if (!me) {
        setTheme(sys);
        return;
      }
      if (readSavedThemeForEmail(me.email) === null) {
        setTheme(sys);
      }
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [me]);

  useEffect(() => {
    if (!getToken()) return;
    void (async () => {
      try {
        const m = await fetchMe();
        setMe(m);
        setScreen('instructions');
      } catch {
        clearToken();
      }
    })();
  }, []);

  const handleNavigation = (page: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin') => {
    const screenMap: Record<typeof page, Screen> = {
      instructions: 'instructions',
      vpn: 'vpn',
      profile: 'profile',
      support: 'support',
      admin: 'admin',
    };
    setScreen(screenMap[page]);
  };

  const handleToggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      if (me) writeSavedThemeForEmail(me.email, next);
      return next;
    });
  };

  const handleLogout = () => {
    clearToken();
    setMe(null);
    setPendingGuestEmail('');
    setScreen('guest1');
  };

  const handleGuestLogin = (user: Me) => {
    setMe(user);
    setScreen('instructions');
  };

  const isAuthenticated = me !== null;

  const renderScreen = () => {
    switch (screen) {
      case 'guest1':
        return (
          <GuestStep1
            onNext={(userEmail) => {
              setPendingGuestEmail(userEmail);
              setScreen('guest2');
            }}
          />
        );
      case 'guest2':
        return (
          <GuestStep2
            email={pendingGuestEmail}
            onBack={() => setScreen('guest1')}
            onLogin={handleGuestLogin}
          />
        );
      case 'instructions':
        return <Instructions />;
      case 'vpn':
        return <VPNSettings canCreateGuestLinks={me?.can_create_guest_links ?? false} />;
      case 'profile':
        return (
          <Profile
            email={me?.email ?? ''}
            role={me?.role ?? 'user'}
            onLogout={handleLogout}
          />
        );
      case 'support':
        return <Support />;
      case 'admin':
        return <AdminPanel />;
      default:
        return null;
    }
  };

  const navScreen: 'instructions' | 'vpn' | 'profile' | 'support' | 'admin' =
    screen === 'admin'
      ? 'admin'
      : screen === 'instructions' ||
          screen === 'vpn' ||
          screen === 'profile' ||
          screen === 'support'
        ? screen
        : 'instructions';

  return (
    <div className="size-full flex">
      {isAuthenticated && (
        <>
          <div className="hidden lg:block">
            <Sidebar
              currentPage={navScreen}
              onNavigate={handleNavigation}
              isAdmin={me?.is_admin ?? false}
            />
          </div>

          <div className="lg:hidden">
            <MobileDrawer
              currentPage={navScreen}
              onNavigate={handleNavigation}
              isAdmin={me?.is_admin ?? false}
            />
          </div>
        </>
      )}

      <main className="flex-1 overflow-auto relative">
        <div className="absolute top-4 right-4 z-50 h-fit w-fit shrink-0">
          <ThemeToggle theme={theme} onToggle={handleToggleTheme} />
        </div>
        {renderScreen()}
      </main>
    </div>
  );
}
