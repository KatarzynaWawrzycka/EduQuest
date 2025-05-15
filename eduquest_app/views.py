from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, TemplateView, DetailView
from django.contrib import messages
from django.views.generic.edit import UpdateView, DeleteView, FormView
from .forms import CustomUserCreationForm, ChildUserCreationForm, PreferencesForm, EmailUpdateForm, \
    ConfirmPasswordForm, UsernameUpdateForm, PasswordUpdateForm, TaskCreateForm, RewardCreateForm
from django.contrib.auth import views as auth_views, authenticate, logout
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import update_session_auth_hash
from .models import CustomUser, Preference, Task, Reward, Points
from django.http import Http404

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
        form = PreferencesForm()
        return render(request, self.template_name, {'form': form, 'child': child})

    def post(self, request, *args, **kwargs):
        child_id = kwargs.get('child_id')
        child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
        form = PreferencesForm(request.POST)

        if form.is_valid():
            child.grade = form.cleaned_data['grade']
            child.preference_filled = True
            child.save()

            Preference.objects.filter(user=child).delete()

            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('subject_'):
                    subject_id = int(field_name.split('_')[1])
                    if value != 0:
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

@login_required
def manage_parent_profile(request):
    user = request.user
    return render(request, 'eduquest_app/manage_parent_profile.html', {'user': user})

@login_required
def manage_child_profile(request, child_id):
    child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
    preference = Preference.objects.filter(user=child).exclude(difficulty=0).select_related('subject') #for subject list
    tasks_raw = Task.objects.filter(user=child).order_by('due_date')

    reward = Reward.objects.filter(user=child, is_active=True).first()

    tasks = []
    for task in tasks_raw:
        try:
            task_preference = Preference.objects.get(user=child, subject=task.subject) #for task list
            points = task_preference.difficulty * 10
        except Preference.DoesNotExist:
            points = 0

        tasks.append({
            'title': task.title,
            'subject': task.subject.name,
            'description': task.description,
            'due_date': task.due_date,
            'status': task.get_status_display(),
            'time': task.time,
            'points': points,
        })

    context = {
        'child': child,
        'preferences': preference,
        'reward': reward,
        'tasks': tasks,
    }

    return render(request, 'eduquest_app/manage_child_profile.html', context)

class EmailUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = EmailUpdateForm
    template_name = 'eduquest_app/email_update.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Email updated successfully!')
        return super().form_valid(form)

class ParentUsernameUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UsernameUpdateForm
    template_name = 'eduquest_app/username_update.html'
    success_url = reverse_lazy('profile')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != CustomUser.Role.PARENT:
            raise Http404("Only parents can access this page.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Username updated successfully!')
        return super().form_valid(form)

class ChildUsernameUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UsernameUpdateForm
    template_name = 'eduquest_app/username_update.html'

    def get_object(self, queryset=None):
        return get_object_or_404(CustomUser, id=self.kwargs['child_id'], parent=self.request.user)

    def get_success_url(self):
        return reverse('manage-child-profile', kwargs={'child_id': self.object.id})

    def form_valid(self, form):
        messages.success(self.request, 'Username updated successfully!')
        return super().form_valid(form)

class ParentPasswordUpdateView(LoginRequiredMixin, FormView):
    model = CustomUser
    form_class = PasswordUpdateForm
    template_name = 'eduquest_app/password_update.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        new_password = form.cleaned_data['password1']
        user = self.request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'Password updated successfully!')
        return redirect('profile')

class ChildPasswordUpdateView(LoginRequiredMixin, FormView):
    model = CustomUser
    form_class = PasswordUpdateForm
    template_name = 'eduquest_app/password_update.html'

    def dispatch(self, request, *args, **kwargs):
        self.child = get_object_or_404(CustomUser, id=kwargs['child_id'], parent=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        new_password = form.cleaned_data['password1']
        self.child.set_password(new_password)
        self.child.save()
        messages.success(self.request, 'Password updated successfully!')
        return redirect('manage-child-profile', child_id=self.child.id)

class DeleteParentProfileView(LoginRequiredMixin, FormView):
    template_name = 'eduquest_app/delete_parent_profile_confirmation.html'
    form_class = ConfirmPasswordForm
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        user = self.request.user
        password = form.cleaned_data['password']

        if authenticate(username=user.username, password=password):
            children = CustomUser.objects.filter(parent=user)
            for child in children:
                Preference.objects.filter(user=child).delete()
                child.delete()

            user.delete()
            logout(self.request)
            messages.success(self.request, 'Your account and all linked children\'s accounts were successfully deleted.')
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Password incorrect.Try again.')
            return self.form_invalid(form)

class DeleteChildProfileView(LoginRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'eduquest_app/delete_child_profile_confirmation.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return get_object_or_404(CustomUser, id=self.kwargs['child_id'], parent=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child'] = self.get_object()
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        Preference.objects.filter(user=self.object).delete()
        response = super().delete(request, *args, **kwargs)

        messages.success(self.request, 'Child profile deleted successfully!')
        return response

class PreferencesUpdateView(LoginRequiredMixin, FormView):
    template_name = 'eduquest_app/preferences_update.html'
    form_class = PreferencesForm
    success_url = reverse_lazy('manage-child-profile')

    def dispatch(self, request, *args, **kwargs):
        self.child = get_object_or_404(CustomUser, id=kwargs['child_id'], parent=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        initial = {'grade': self.child.grade}
        preferences = Preference.objects.filter(user=self.child)

        for p in preferences:
            initial[f'subject_{p.subject_id}'] = p.difficulty

        form = self.form_class(initial=initial)
        return render(request, self.template_name, {'form': form, 'child': self.child})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            self.child.grade = form.cleaned_data['grade']
            self.child.preference_filled = True
            self.child.save()

            Preference.objects.filter(user=self.child).delete()

            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('subject_') and value != 0:
                    subject_id = int(field_name.split('_')[1])
                    Preference.objects.create(
                        user=self.child,
                        subject_id=subject_id,
                        difficulty=value,
                    )

            messages.success(request, 'Preferences updated successfully!')
            return redirect('manage-child-profile', child_id=self.child.id)

        return render(request, self.template_name, {'form': form, 'child': self.child})

class RewardCreateView(LoginRequiredMixin, CreateView):
    model = Reward
    form_class = RewardCreateForm
    template_name = 'eduquest_app/reward_create.html'

    def dispatch(self, request, *args, **kwargs):
        self.child = get_object_or_404(CustomUser, id=kwargs['child_id'], parent=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        Reward.objects.filter(user=self.child, is_active=True).update(is_active=False)
        form.instance.user = self.child
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('manage-child-profile', kwargs={'child_id': self.kwargs['child_id']})

class RewardEditView(LoginRequiredMixin, UpdateView):
    model = Reward
    fields = ['name', 'points_required']
    template_name = 'eduquest_app/reward_edit.html'

    def get_queryset(self):
        child_id = self.kwargs.get('child_id')
        return Reward.objects.filter(
            user_id=child_id,
            user__parent=self.request.user
        )

    def get_success_url(self):
        return reverse('manage-child-profile', kwargs={'child_id': self.kwargs['child_id']})


class RewardDeleteView(LoginRequiredMixin, DeleteView):
    model = Reward
    template_name = 'eduquest_app/reward_delete.html'

    def get_queryset(self):
        child_id = self.kwargs.get('child_id')

        return Reward.objects.filter(
            user_id=child_id,
            user__parent=self.request.user
        )

    def get_success_url(self):
        child_id = self.kwargs.get('child_id')
        return reverse('manage-child-profile', kwargs={'child_id': child_id})

class TasksListView(LoginRequiredMixin, TemplateView):
    """
    Tasks List
    for currently logged-in user
    """
    template_name = 'eduquest_app/task_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = (Task.objects
                            .filter(user=self.request.user)
                            .order_by('due_date'))
        return context

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'eduquest_app/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        task = self.object

        try:
            preference = Preference.objects.get(user=user, subject=task.subject)
            points = preference.difficulty * 10
        except Preference.DoesNotExist:
            points = 0

        context['points'] = points
        return context

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskCreateForm
    template_name = 'eduquest_app/task_create.html'
    success_url = reverse_lazy('tasks')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        task = form.save(commit=False)
        task.user = self.request.user
        task.status = Task.Status.TO_DO.value
        task.save()
        return super().form_valid(form)

class TaskEditView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskCreateForm
    template_name = 'eduquest_app/task_edit.html'
    success_url = reverse_lazy('tasks')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'eduquest_app/task_delete.html'
    success_url = reverse_lazy('tasks')

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)