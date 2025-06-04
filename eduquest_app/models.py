from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _


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

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PARENT
    )

    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children'
    )

    def clean(self):
        super().clean()
        if self.role == CustomUser.Role.CHILD and not self.parent:
            raise ValidationError("Child's account has to be paired with its parent")

    def save(self, *args, **kwargs):
        if not self.pk and self.role == CustomUser.Role.PARENT:
            self.parent = None
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.role == CustomUser.Role.CHILD:
            Preference.objects.filter(user=self).delete()
            Task.objects.filter(user=self).delete()
            Reward.objects.filter(user=self).delete()
            Points.objects.filter(user=self).delete()
        elif self.role == CustomUser.Role.PARENT:
            for child in self.children.all():
                child.delete()

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

class Subject(models.Model):
    class SubjectsEnum(models.TextChoices):
        MATHEMATICS = 'mathematics', _('Mathematics')
        BIOLOGY = 'polish_language', _('Polish Language')
        CHEMISTRY = 'english_language', _('English Language')
        PHYSICS = 'history', _('History')
        HISTORY = 'science', _('Science')
        GEOGRAPHY = 'computer_science', _('Computer Science')

    name = models.CharField(
        max_length=50,
        choices=SubjectsEnum.choices,
        unique=True,
    )

    def __str__(self):
        return str(self.SubjectsEnum(self.name).label)

class Preference(models.Model):

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    difficulty = models.IntegerField(choices=[(i, label) for i, label in enumerate(
        [_('Not applicable'), _('Very easy'), _('Quite easy'), _('Normal'), _('Quite hard'), _('Very hard')], start=0)])

    def __str__(self):
        return f"{self.user.username} - {self.subject.name} ({self.difficulty})"

class Reward(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    points_required = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_active=True),
                name='unique_active_reward_per_child'
            )
        ]
        verbose_name = "Reward"
        verbose_name_plural = "Rewards"

class Task(models.Model):
    class Status(models.TextChoices):
        TO_DO = 'to_do', _('To do')
        STARTED = 'started', _('Started')
        DONE = 'done', _('Done')
        OVERDUE = 'overdue', _('Overdue')

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    time = models.PositiveIntegerField(help_text=_("Time in minutes"))
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.TO_DO
    )

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

class Points(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    points = models.PositiveIntegerField()
    awarded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.points} points ({self.awarded_at.date()})"

    class Meta:
        verbose_name = "Points"
        verbose_name_plural = "Points' history"
