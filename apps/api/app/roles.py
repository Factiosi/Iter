"""Роли whitelist-пользователей (отображение в профиле и права)."""

ROLE_USER = "user"
ROLE_MODERATOR = "moderator"
ROLE_ADMINISTRATOR = "administrator"

VALID_ROLES = frozenset({ROLE_USER, ROLE_MODERATOR, ROLE_ADMINISTRATOR})

# Роли, которые можно выставить записи в whitelist (Dominus только у factiosi@gmail.com вне таблицы)
WHITELIST_ASSIGNABLE_ROLES = frozenset({ROLE_USER, ROLE_MODERATOR})


def normalize_role(value: str | None) -> str:
    if not value or value not in VALID_ROLES:
        return ROLE_USER
    return value


def can_create_guest_links(role: str) -> bool:
    return role in (ROLE_MODERATOR, ROLE_ADMINISTRATOR)
