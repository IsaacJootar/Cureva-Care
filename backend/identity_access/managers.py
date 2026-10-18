from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for the custom User model.

    Accounts are invite-only: an admin creates the user and sets an initial
    password (the user can change it later). A user created without a password
    gets an unusable one until an admin sets it or they use a magic link.
    Authorization comes from the admin-assigned role/scope on the record.
    """

    use_in_migrations = True

    def create_user(self, email, name, role, password=None, **extra_fields):
        if not email:
            raise ValueError("A user must have an email address.")
        if not role:
            raise ValueError("A user must have a role.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, name=name, role=role, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, role="systems_admin", **extra_fields):
        # Emergency/CLI use only — the product has no Django-admin surface.
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email=email, name=name, role=role, **extra_fields)
