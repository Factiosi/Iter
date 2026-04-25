import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from './ui/utils';

/** Общий вид основных кнопок портала (инструкции, VPN, вход, профиль и т.д.) */
export const appPrimaryButtonClassName =
  'inline-flex items-center justify-center gap-2 min-h-[2.75rem] px-4 font-semibold text-sm text-[var(--foreground)] bg-[var(--button-bg)] border border-[var(--button-border)] rounded-lg hover:opacity-80 transition-opacity duration-200 disabled:pointer-events-none disabled:opacity-50';

export type AppPrimaryButtonProps = React.ComponentProps<'button'> & {
  asChild?: boolean;
};

export function AppPrimaryButton({ className, asChild = false, ...props }: AppPrimaryButtonProps) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={cn(appPrimaryButtonClassName, className)} {...props} />;
}
