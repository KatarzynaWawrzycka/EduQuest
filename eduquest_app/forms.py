from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

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