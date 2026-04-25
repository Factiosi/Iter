const LABELS: Record<string, string> = {
  user: 'Usor',
  moderator: 'Hospes',
  administrator: 'Dominus',
};

export function roleLabel(role: string): string {
  const key = role.trim().toLowerCase();
  return LABELS[key] ?? role;
}
