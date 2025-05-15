from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.utils import timezone

from .models import CustomUser, Subject, Task, Preference, Reward

DIFFICULTY_CHOICES = [
    (0, 'Not applicable'),
    (1, 'Very easy'),
    (2, 'Quite easy'),
    (3, 'Normal'),
    (4, 'Quite hard'),
    (5, 'Very hard'),
]

class ConfirmPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

class CustomUserCreationForm(UserCreationForm):
    """
    Custom User Creation Form
    Registration form for a PARENT
    Required - email, username, password with confirmation (based on built-in password validation)
    """
    email = forms.EmailField(required=True, help_text='Required. Please enter your email address.')

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PARENT # setting default PARENT role
        if commit:
            user.save()
        return user

class ChildUserCreationForm(UserCreationForm):
    """
    Child User Creation Form
    Registration form for a CHILD
    Required - username, password with confirmation (based on built-in password validation) - no email required
    """
    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2')

class CustomUserAuthenticationForm(AuthenticationForm):
    """
    Custom User Authentication Form
    Log in action
    Required - username, password
    """
    class Meta:
        model = CustomUser
        fields = ('username', 'password')

class PreferencesForm(forms.Form):
    grade = forms.ChoiceField(choices=[(i, f"Grade {i}") for i in range (1, 5)], label="Select grade")

    def __init__(self, *args, **kwargs):
        subjects = Subject.objects.all()
        super().__init__(*args, **kwargs)

        for subject in subjects:
            self.fields[f'subject_{subject.id}'] = forms.ChoiceField(
                choices=DIFFICULTY_CHOICES,
                label=subject.name,
                required=False,
            )

class EmailUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, help_text='New email address')

    class Meta:
        model = CustomUser
        fields = ['email']

class UsernameUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, help_text='New username')
    class Meta:
        model = CustomUser
        fields = ['username']

class PasswordUpdateForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label="New password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data

class RewardCreateForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ['name', 'points_required']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Reward name'}),
            'points_required': forms.NumberInput(attrs={'min': 10}),
        }
        labels = {
            'name': 'Reward name',
            'points_required': 'Points required',
        }

class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'subject', 'description', 'due_date', 'time']

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            subjects = Subject.objects.filter(preference__user=self.user, preference__difficulty__gt=0)
            self.fields['subject'].queryset = subjects

    def clean(self):
        cleaned_data = super().clean()
        #time = cleaned_data.get('time')
        due_date = cleaned_data.get('due_date')

        if due_date and due_date < timezone.localdate():
            self.add_error('due_date', "Due date cannot be in the past.")

        '''
         if time is not None and time < 5:
            self.add_error('time', "Time must be at least 5 minutes.")
        '''