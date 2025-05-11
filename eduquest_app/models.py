from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class CustomUser(AbstractUser):
    """
    Custom User model
    Inherits from built-in AbstractUser
    Modifications = optional email - not required for child's account, user role (Parent/Child) - for different access, grade for preferences form, check if preferences are set
    """
    email = models.EmailField(blank=True, null=True)
    grade = models.PositiveIntegerField(blank=True, null=True)
    preference_filled = models.BooleanField(default=False)

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

class Subject(models.Model):
    """
    Subject model
    Subjects list (id, name)
    """
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Preference(models.Model):
    """
    Preference model
    Links difficulty level to a subject to a user (child)
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    difficulty = models.IntegerField(choices=[(i, label) for i, label in enumerate(
        ['Very easy', 'Quite easy', 'Normal', 'Quite hard', 'Very hard'], start=1)])

    def __str__(self):
        return f"{self.user.username} - {self.subject.name} ({self.difficulty})"