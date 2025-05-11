from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class CustomUser(AbstractUser):
    """
    Custom User model
    Inherits from built-in AbstractUser
    Modifications = email is optional - not required for child's account, user has a role (Parent/Child) - for different access
    """
    email = models.EmailField(blank=True, null=True)

    class Role(models.TextChoices):
        CHILD = 'child', 'Child'
        PARENT = 'parent', 'Parent'

    # All new users are defined as PARENTS - only logges in parent can register a child
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PARENT
    )

    # parent-child relation
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children'
    )

    # validation - child's account has to be paired with parent's one
    def clean(self):
        super().clean()
        if self.role == CustomUser.Role.CHILD and not self.parent:
            raise ValidationError("Child's account has to be paired with its parent")

    # creating new user
    def save(self, *args, **kwargs):
        #if the new user is a parent - delete parent relation
        if not self.pk and self.role == CustomUser.Role.PARENT:
            self.parent = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Użytkownik"
        verbose_name_plural = "Użytkownicy"