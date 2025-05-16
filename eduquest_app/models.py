from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import Q


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
        ['Not applicable', 'Very easy', 'Quite easy', 'Normal', 'Quite hard', 'Very hard'], start=0)])

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
        TO_DO = 'to_do', 'To do'
        STARTED = 'started', 'Started'
        DONE = 'done', 'Done'
        OVERDUE = 'overdue', 'Overdue'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    time = models.PositiveIntegerField(help_text="Time in minutes")
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