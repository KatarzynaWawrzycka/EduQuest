from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Subject

DIFFICULTY_CHOICES = [
    (0, 'Not applicable'),
    (1, 'Very easy'),
    (2, 'Quite easy'),
    (3, 'Normal'),
    (4, 'Quite hard'),
    (5, 'Very hard'),
]

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

class PreferenceForm(forms.Form):
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

class ParentProfileEditForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="New password", required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm new password", required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and not password2:
            raise forms.ValidationError("Please confirm your new password.")

        if password2 and not password1:
            raise forms.ValidationError("Please enter your new password.")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        if not password1 and not password2:
            return None

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')

        if password:
            user.set_password(password)

        if commit:
            user.save()
        return user

class ChildProfileEditForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="New password", required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm new password", required=False)

    class Meta:
        model = CustomUser
        fields = ['username']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and not password2:
            raise forms.ValidationError("Please confirm your new password.")

        if password2 and not password1:
            raise forms.ValidationError("Please enter your new password.")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        if not password1 and not password2:
            return None

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')

        if password:
            user.set_password(password)

        if commit:
            user.save()
        return user