from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import CustomUser, Subject, Task, Reward

DIFFICULTY_CHOICES = [
    (0, _('Not applicable')),
    (1, _('Very easy')),
    (2, _('Quite easy')),
    (3, _('Normal')),
    (4, _('Quite hard')),
    (5, _('Very hard')),
]

class ConfirmPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label=_("Confirm password"))

class CustomUserCreationForm(UserCreationForm):

    email = forms.EmailField(required=True, help_text=_('Required. Please enter your email address.'))

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')

        if email and CustomUser.objects.filter(email=email).exists():
            self.add_error('email', _("This email is already taken."))

        if username and CustomUser.objects.filter(username=username).exists():
            self.add_error('username', _("This username is already taken."))

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PARENT  # setting default PARENT role
        if commit:
            user.save()
        return user

class ChildUserCreationForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError(_('This username is already in use.'))
        return username

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from .models import CustomUser

class CustomUserAuthenticationForm(AuthenticationForm):

    username = forms.CharField(label=_("Login"))

    class Meta:
        model = CustomUser
        fields = ('username', 'password')

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            try:
                user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                self.add_error('username', _('User with this username does not exist.'))
                return cleaned_data

            user = authenticate(username=username, password=password)
            if user is None:
                self.add_error('password', _('Incorrect password.'))
        return cleaned_data

class PreferencesForm(forms.Form):
    grade = forms.ChoiceField(
        choices=[(i, _("Grade %d") % i) for i in range(1, 5)],
        label=_("Select grade"),
        required=True,
        widget=forms.Select(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Iterujemy po enum SubjectsEnum, nie po bazie danych
        for subject_value, subject_label in Subject.SubjectsEnum.choices:
            self.fields[f'subject_{subject_value}'] = forms.ChoiceField(
                choices=DIFFICULTY_CHOICES,
                label=subject_label,
                required=False,
            )

    def clean(self):
        cleaned_data = super().clean()
        has_subject_selected = any(
            cleaned_data.get(field) not in [None, '', '0']
            for field in cleaned_data if field.startswith('subject_')
        )
        if not has_subject_selected:
            raise forms.ValidationError(_("Please select a difficulty level for at least one subject."))
        return cleaned_data

class EmailUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, help_text=_('New email address'))

    class Meta:
        model = CustomUser
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(_("This email is already in use."))
        return email

class UsernameUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, help_text=_('New username'))
    class Meta:
        model = CustomUser
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(_("This username is already taken."))
        return username

class PasswordUpdateForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label=_("New password"), help_text=_("Set new password"))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("Confirm password"), help_text=_("Repeat new password"))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError(_("Passwords don't match"))
        return cleaned_data

class RewardCreateForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ['name', 'points_required']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Reward name')}),
            'points_required': forms.NumberInput(attrs={'min': 10}),
        }
        labels = {
            'name': _('Reward name'),
            'points_required': _('Points required'),
        }

    def clean_points_required(self):
        points = self.cleaned_data.get('points_required')
        if points < 10:
            raise forms.ValidationError(_("Reward must require at least 10 points."))
        return points

class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'subject', 'description', 'due_date', 'time']

        labels = {
            'title': _('Title'),
            'subject': _('Subject'),
            'description': _('Description'),
            'due_date': _('Due date'),
            'time': _('Time'),
        }

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            subjects = Subject.objects.filter(preference__user=self.user, preference__difficulty__gt=0)
            self.fields['subject'].queryset = subjects

    def clean(self):
        cleaned_data = super().clean()
        due_date = cleaned_data.get('due_date')
        time = cleaned_data.get('time')

        if due_date and due_date < timezone.localdate():
            self.add_error('due_date', _("Due date cannot be in the past."))

        if time is not None and time < 5:
            self.add_error('time', _("Time must be at least 5 minutes."))
