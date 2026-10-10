from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the custom User model.

    There are no passwords in this product (magic-link / SSO only, see
    cureva-docs/00-START-HERE.md). Users are created with an unusable password;
    identity is established by the login method, authorization by the
    admin-assigned role/scope on the record.
    """

    use_in_migrations = True

    def create_user(self, email, name, role, **extra_fields):
        if not email:
            raise ValueError("A user must have an email address.")
        if not role:
            raise ValueError("A user must have a role.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, name=name, role=role, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, role="systems_admin", **extra_fields):
        # Emergency/CLI use only — the product has no Django-admin surface.
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email=email, name=name, role=role, **extra_fields)
