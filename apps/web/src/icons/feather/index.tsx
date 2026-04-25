import bookOpen from '@/assets/feather/book-open.svg?raw';
import settings from '@/assets/feather/settings.svg?raw';
import link2 from '@/assets/feather/link-2.svg?raw';
import link from '@/assets/feather/link.svg?raw';
import externalLink from '@/assets/feather/external-link.svg?raw';
import eye from '@/assets/feather/eye.svg?raw';
import user from '@/assets/feather/user.svg?raw';
import logOut from '@/assets/feather/log-out.svg?raw';
import shield from '@/assets/feather/shield.svg?raw';
import helpCircle from '@/assets/feather/help-circle.svg?raw';
import download from '@/assets/feather/download.svg?raw';
import key from '@/assets/feather/key.svg?raw';
import userPlus from '@/assets/feather/user-plus.svg?raw';
import copy from '@/assets/feather/copy.svg?raw';
import check from '@/assets/feather/check.svg?raw';
import menu from '@/assets/feather/menu.svg?raw';
import x from '@/assets/feather/x.svg?raw';
import chevronDown from '@/assets/feather/chevron-down.svg?raw';
import mail from '@/assets/feather/mail.svg?raw';
import send from '@/assets/feather/send.svg?raw';
import arrowLeft from '@/assets/feather/arrow-left.svg?raw';
import plus from '@/assets/feather/plus.svg?raw';
import trash2 from '@/assets/feather/trash-2.svg?raw';
import moon from '@/assets/feather/moon.svg?raw';
import sun from '@/assets/feather/sun.svg?raw';

const RAW = {
  'book-open': bookOpen,
  settings,
  'link-2': link2,
  link,
  'external-link': externalLink,
  eye,
  user,
  'log-out': logOut,
  shield,
  'help-circle': helpCircle,
  download,
  key,
  'user-plus': userPlus,
  copy,
  check,
  menu,
  x,
  'chevron-down': chevronDown,
  mail,
  send,
  'arrow-left': arrowLeft,
  plus,
  'trash-2': trash2,
  moon,
  sun,
} as const;

export type FeatherIconName = keyof typeof RAW;

export type FeatherIconProps = {
  name: FeatherIconName;
  size?: number;
  className?: string;
};

/**
 * Локальные SVG Feather Icons (`src/assets/feather/`), без загрузки с feathericons.com.
 */
export function FeatherIcon({ name, size = 20, className = '' }: FeatherIconProps) {
  const raw = RAW[name];
  let svg = raw
    .replace(/\bwidth="24"/g, 'width="100%"')
    .replace(/\bheight="24"/g, 'height="100%"');
  svg = svg.replace(/<svg\b/, `<svg class="${className.replace(/"/g, '&quot;')}" `);
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center text-current [&>svg]:block"
      style={{ width: size, height: size }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
