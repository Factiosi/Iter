import logoLight from '@brand/logo-light.png';
import logoDark from '@brand/logo-dark.png';

type LogoProps = {
  /** Сайдбар: компактный блок; auth — экран входа */
  variant?: 'default' | 'auth';
  /**
   * Макс. ширина контейнера на экране входа (px). Высота задаётся отдельно — PNG может быть очень большим,
   * на экране масштабируется через object-contain.
   */
  authWidthPx?: number;
};

/** Ограничиваем отрисовку: исходные PNG могут быть тысячи пикселей. */
const SIDEBAR_MAX_W_PX = 220;
const SIDEBAR_MAX_H_PX = 72;

const AUTH_MAX_W_DEFAULT_PX = 280;
const AUTH_MAX_H_PX = 120;

export function Logo({ variant = 'default', authWidthPx = AUTH_MAX_W_DEFAULT_PX }: LogoProps) {
  const imgClass =
    'absolute left-1/2 top-1/2 max-h-full max-w-full -translate-x-1/2 -translate-y-1/2 object-contain object-center';

  if (variant === 'default') {
    return (
      <div
        className="relative mx-auto shrink-0"
        style={{ width: SIDEBAR_MAX_W_PX, height: SIDEBAR_MAX_H_PX }}
      >
        <img
          src={logoLight}
          alt="Iter.Factiosi"
          className={`${imgClass} dark:hidden`}
          loading="lazy"
          decoding="async"
        />
        <img
          src={logoDark}
          alt="Iter.Factiosi"
          className={`${imgClass} hidden dark:block`}
          loading="lazy"
          decoding="async"
        />
      </div>
    );
  }

  return (
    <div
      className="relative mx-auto flex shrink-0 items-center justify-center overflow-hidden"
      style={{
        width: `min(100%, ${authWidthPx}px)`,
        maxWidth: authWidthPx,
        height: AUTH_MAX_H_PX,
      }}
    >
      <img
        src={logoLight}
        alt="Iter.Factiosi"
        className={`${imgClass} dark:hidden`}
        loading="eager"
        decoding="async"
      />
      <img
        src={logoDark}
        alt="Iter.Factiosi"
        className={`${imgClass} hidden dark:block`}
        loading="eager"
        decoding="async"
      />
    </div>
  );
}
