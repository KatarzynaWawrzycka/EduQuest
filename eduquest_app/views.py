from pipes import Template

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, TemplateView
from django.contrib import messages
from .forms import CustomUserCreationForm, ChildUserCreationForm, PreferenceForm
from django.contrib.auth import views as auth_views
from django.shortcuts import render, get_object_or_404, redirect

from .models import CustomUser, Preference


def index(request):
    """
    Index view
    Rendering template
    """
    return render(request, 'eduquest_app/index.html')

class SignUpView(CreateView):
    """
    Sign up view
    for PARENT
    Rendering template and redirecting to LOG IN
    """
    form_class = CustomUserCreationForm
    template_name = 'eduquest_app/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'User registered successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error during form validation')
        return super().form_invalid(form)

class ChildUserCreationView(LoginRequiredMixin, CreateView):
    """
    Child user creation view (sign up view)
    for CHILD
    Rendering template and redirecting to LOG IN
    """
    model = CustomUser
    form_class = ChildUserCreationForm
    template_name = 'eduquest_app/add_child_user.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        child = form.save(commit=False)
        child.role = CustomUser.Role.CHILD # setting role CHILD
        child.parent = self.request.user # pairing with PARENT (requesting the form)
        child.save()
        messages.success(self.request, f'Child {child.username} registered successfully!')
        return super().form_valid(form)

class LoginView(auth_views.LoginView):
    """
    Login view
    for all users
    Rendering template and redirecting to PROFILE (parent) or TASKS (child)
    """
    template_name = 'eduquest_app/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.role == 'parent':
            return reverse('profile')
        elif user.role == 'child':
            if not user.preference_filled:
                return reverse('child-first-login')
            return reverse('tasks')
        return reverse('index')

class ChildFirstLoginView(LoginRequiredMixin, TemplateView):
    template_name = 'eduquest_app/child_first_login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = 'Your preferences aren\'t set yet. Your parent must fill out a form first.'
        return context

class LogoutView(auth_views.LogoutView):
    """
    Logout view
    Redirecting back to log in ----------------------------------------CHANGE TO INDEX ONCE DONE
    """
    next_page = "login"

class SetPreferencesView(LoginRequiredMixin, TemplateView):
    template_name = 'eduquest_app/set_preference.html'

    def get(self, request, *args, **kwargs):
        child_id = kwargs.get('child_id')
        child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
        form = PreferenceForm()
        return render(request, self.template_name, {'form': form, 'child': child})

    def post(self, request, *args, **kwargs):
        child_id = kwargs.get('child_id')
        child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
        form = PreferenceForm(request.POST)

        if form.is_valid():
            child.grade = form.cleaned_data['grade']
            child.preference_filled = True
            child.save()

            Preference.objects.filter(user=child).delete()

            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('subject_') and value:
                    subject_id = int(field_name.split('_')[1])
                    Preference.objects.create(
                        user=child,
                        subject_id=subject_id,
                        difficulty=value,
                    )

            messages.success(request, 'Your preferences were successfully updated!')
            return redirect('profile')

        return render(request, self.template_name, {'form': form, 'child': child})

class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Profile view
    for PARENT
    Displaying profile information + administration panel - managing parent's account + their children's accounts
    """
    template_name = 'eduquest_app/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['username'] = user.username
        context['role'] = user.get_role_display()

        # displaying children's accounts linked to the parent
        if user.role == 'parent':
            children = user.children.all() or []
            children_data = []
            has_children_without_preferences = False

            for child in children:
                has_preference = child.preference_filled
                if not has_preference:
                    has_children_without_preferences = True
                children_data.append({
                    'child': child,
                    'has_preference': has_preference,
                })

            context['children_data'] = children_data
            context['has_children_without_preferences'] = has_children_without_preferences

        return context

class TasksView(LoginRequiredMixin, TemplateView):
    """
    Tasks view

    """
    template_name = 'eduquest_app/tasks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['username'] = user.username
        context['role'] = user.get_role_display()
        return context

