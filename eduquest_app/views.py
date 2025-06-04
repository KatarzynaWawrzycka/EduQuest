from datetime import timedelta, date
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, F
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
import json
from django.utils.timezone import localdate
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, TemplateView, DetailView
from django.contrib import messages
from django.views.generic.edit import UpdateView, DeleteView, FormView
from .forms import CustomUserCreationForm, ChildUserCreationForm, PreferencesForm, EmailUpdateForm, \
    ConfirmPasswordForm, UsernameUpdateForm, PasswordUpdateForm, TaskCreateForm, RewardCreateForm, \
    CustomUserAuthenticationForm
from django.contrib.auth import views as auth_views, authenticate, logout
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import update_session_auth_hash
from .models import CustomUser, Preference, Task, Reward, Points, Subject
from django.http import Http404, JsonResponse, HttpResponse, request
from django.core.paginator import Paginator


def index(request):

    return render(request, 'eduquest_app/index.html')

class SignUpView(CreateView):

    form_class = CustomUserCreationForm
    template_name = 'eduquest_app/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session['registered'] = True
        return response

class ChildUserCreationView(LoginRequiredMixin, CreateView):

    model = CustomUser
    form_class = ChildUserCreationForm
    template_name = 'eduquest_app/add_child_user.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        child = form.save(commit=False)
        child.role = CustomUser.Role.CHILD
        child.parent = self.request.user
        child.save()
        messages.success(self.request, _('Child %(username) registered successfully!') % {'username': child.username})
        return super().form_valid(form)

class LoginView(auth_views.LoginView):

    template_name = 'eduquest_app/login.html'
    authentication_form = CustomUserAuthenticationForm

    def get_success_url(self):
        user = self.request.user
        if user.role == 'parent':
            return reverse('profile')
        elif user.role == 'child':
            if not user.preference_filled:
                return reverse('child-first-login')
            return reverse('tasks')
        return reverse('index')

    def get(self, request, *args, **kwargs):
        if request.session.get('registered'):
            messages.success(request, _('User registered successfully!'))
            del request.session['registered']
        return super().get(request, *args, **kwargs)

class ChildFirstLoginView(LoginRequiredMixin, TemplateView):
    template_name = 'eduquest_app/child_first_login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = _('Your preferences aren\'t set yet. Your parent must fill out a form first.')
        return context

class LogoutView(auth_views.LogoutView):

    next_page = "index"

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
                    subject_key = field_name.split('subject_')[1]

                    if value and value != '0':
                        try:
                            difficulty = int(value)
                        except ValueError:
                            continue

                        subject = Subject.objects.filter(name=subject_key).first()
                        if subject:
                            Preference.objects.create(
                                user=child,
                                subject=subject,
                                difficulty=difficulty,
                            )

                        print(f"Created Preference for {child} - {subject} - difficulty {difficulty}")

            messages.success(request, _('Your preferences were successfully updated!'))
            return redirect('profile')

        return render(request, self.template_name, {'form': form, 'child': child})

class ProfileView(LoginRequiredMixin, TemplateView):

    template_name = 'eduquest_app/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        context['username'] = user.username
        context['role'] = user.get_role_display()

        if user.role == 'parent':
            children = user.children.all() if hasattr(user, 'children') else []
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
def manage_child_profile(request, child_id):
    child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
    today = localdate()
    todayP = date.today()

    preferences = Preference.objects.filter(user=child).exclude(difficulty=0).select_related('subject')
    preference_map = {pref.subject: pref.difficulty for pref in preferences}

    reward = Reward.objects.filter(user=child, is_active=True).first()
    if reward:
        earned_points = Points.objects.filter(
            user=child,
            awarded_at__gte=reward.created_at
        ).aggregate(total=Sum('points'))['total'] or 0
        reward_achieved = earned_points >= reward.points_required
    else:
        earned_points = 0
        reward_achieved = False

    Task.objects.filter(
        user=child,
        due_date__lt=today,
    ).filter(
        Q(finished_at__isnull=True) | Q(finished_at__gt=F('due_date'))
    ).exclude(
        status=Task.Status.OVERDUE.value
    ).update(status=Task.Status.OVERDUE.value)

    queryset = Task.objects.filter(user=child).select_related('subject')
    started_tasks = queryset.filter(status=Task.Status.STARTED.value)
    todo_tasks = queryset.filter(status=Task.Status.TO_DO.value).order_by('due_date')
    done_tasks = queryset.filter(status=Task.Status.DONE.value).order_by('-finished_at')
    overdue_tasks = queryset.filter(status=Task.Status.OVERDUE.value)

    points_map = {
        p.task_id: p.points for p in Points.objects.filter(task__in=done_tasks)
    }

    def serialize(tasks_qs):
        result = []
        for task in tasks_qs:
            if task.status == Task.Status.DONE.value:
                points = points_map.get(task.id, 0)
            elif task.status == Task.Status.OVERDUE.value:
                points = 0
            else:
                diff = preference_map.get(task.subject, 0)
                points = diff * 10

            result.append({
                'id': task.id,
                'title': task.title,
                'subject': task.subject,
                'description': task.description,
                'due_date': task.due_date,
                'status': task.get_status_display(),
                'time': task.time,
                'points': points,
            })
        return result

    context = {
        'child': child,
        'preferences': preferences,
        'reward': reward,
        'earned_points': earned_points,
        'reward_achieved': reward_achieved,
        'started_tasks': serialize(started_tasks),
        'todo_tasks': serialize(todo_tasks),
        'done_tasks': serialize(done_tasks),
        'overdue_tasks': serialize(overdue_tasks),
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
        messages.success(self.request, _('Email updated successfully!'))
        return super().form_valid(form)

class ParentUsernameUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UsernameUpdateForm
    template_name = 'eduquest_app/username_update.html'
    success_url = reverse_lazy('profile')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != CustomUser.Role.PARENT:
            raise Http404(_("Only parents can access this page."))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _('Username updated successfully!'))
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
        messages.success(self.request, _('Username updated successfully!'))
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
        messages.success(self.request, _('Password updated successfully!'))
        return redirect('profile')

    def form_invalid(self, form):
        messages.error(self.request, _("Passwords don't match."))
        return super().form_invalid(form)

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
        messages.success(self.request, _('Password updated successfully!'))
        return redirect('manage-child-profile', child_id=self.child.id)

    def form_invalid(self, form):
        messages.error(self.request, _("Passwords don't match."))
        return super().form_invalid(form)

class DeleteParentProfileView(LoginRequiredMixin, FormView):
    template_name = 'eduquest_app/delete_parent_profile_confirmation.html'
    form_class = ConfirmPasswordForm
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        user = self.request.user
        password = form.cleaned_data['password']

        if authenticate(username=user.username, password=password):
            user.delete()
            logout(self.request)
            messages.success(self.request,_('Your account and all linked children\'s accounts were successfully deleted.'))
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, _('Password incorrect.Try again.'))
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
        self.object.delete()
        messages.success(self.request, _('Child profile deleted successfully!'))
        return redirect(self.get_success_url())

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
            initial[f'subject_{p.subject.name}'] = p.difficulty

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
                    subject_key = field_name.split('_', 1)[1]
                    subject = Subject.objects.filter(name=subject_key).first()
                    if subject:
                        Preference.objects.create(
                            user=self.child,
                            subject=subject,
                            difficulty=value,
                        )

            messages.success(request, _('Preferences updated successfully!'))
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

class RewardClaimView(LoginRequiredMixin, View):
    def post(self, request, child_id, reward_id):
        child = get_object_or_404(CustomUser, id=child_id, parent=request.user)
        reward = get_object_or_404(Reward, id=reward_id, user=child, is_active=True)

        reward.is_active = False
        reward.save(update_fields=['is_active'])

        messages.success(request, _('Reward "%(reward_name)s" marked as claimed') % {'reward_name': reward.name})
        return redirect('manage-child-profile', child_id=child.id)


class TasksListView(LoginRequiredMixin, TemplateView):
    template_name = 'eduquest_app/task_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = localdate()

        todayP = date.today()
        points_today = Points.objects.filter(
            user=user,
            awarded_at__gte=todayP,
        ).aggregate(total=Sum('points'))['total'] or 0

        Task.objects.filter(
            user=user,
            due_date__lt=today,
        ).filter(
            Q(finished_at__isnull=True) | Q(started_at__gt=F('due_date'))
        ).exclude(
            status=Task.Status.OVERDUE.value
        ).update(status=Task.Status.OVERDUE.value)

        querySet = Task.objects.filter(user=user)
        started = querySet.filter(status=Task.Status.STARTED.value)
        todo = querySet.filter(status=Task.Status.TO_DO.value).order_by('due_date')
        done_querySet = querySet.filter(status=Task.Status.DONE.value).order_by('-finished_at')
        overdue = querySet.filter(status=Task.Status.OVERDUE.value)

        todo_paginator = Paginator(todo, 5)
        toto_page_number = self.request.GET.get('todo_page')
        todo_page = todo_paginator.get_page(toto_page_number)

        done_paginator = Paginator(done_querySet, 5)
        page_number = self.request.GET.get('done_page')
        done_page = done_paginator.get_page(page_number)

        overdue_paginator = Paginator(overdue, 5)
        overdue_page_number = self.request.GET.get('overdue_page')
        overdue_page = overdue_paginator.get_page(overdue_page_number)

        points_map = {
            p.task_id: p.points for p in Points.objects.filter(task__in=done_querySet)
        }

        prefs = {
            p.subject: p.difficulty for p in self.request.user.preference_set.all()
        }

        def serialize(tasks_querySet):
            out = []
            for task in tasks_querySet:
                if task.status == Task.Status.DONE.value:
                    points = points_map.get(task.id, 0)
                elif task.status == Task.Status.OVERDUE.value:
                    points = 0
                else:
                    diff = prefs.get(task.subject, 0)
                    points = diff * 10

                out.append({
                    'id': task.id,
                    'title': task.title,
                    'subject': task.subject.get_name_display(),
                    'description': task.description,
                    'due_date': task.due_date,
                    'status': task.get_status_display(),
                    'time': task.time,
                    'points': points,
                    'button_label': _('Continue') if task.status == Task.Status.STARTED.value else _('Start'),
                    'disabled': (task.status not in [Task.Status.TO_DO.value, Task.Status.STARTED.value]),
                })
            return out

        show_param = self.request.GET.get('show')

        context.update({
            'started_tasks': serialize(started),
            'todo_tasks': serialize(todo_page.object_list),
            'todo_page': todo_page,
            'todo_paginator': todo_paginator,

            'done_tasks': serialize(done_page.object_list),
            'done_page': done_page,
            'done_paginator': done_paginator,

            'overdue_tasks': serialize(overdue_page.object_list),
            'overdue_page': overdue_page,
            'overdue_paginator': overdue_paginator,

            'done_page_number': page_number,
            'show': show_param,
            'show_done': show_param == 'done',

            'points_today': points_today,
        })

        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'eduquest_app/task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        task = self.object

        is_parent_of_task_user = (hasattr(user, 'children') and task.user in user.children.all())

        if task.status == Task.Status.DONE.value:
            points_obj = Points.objects.filter(task=task).first()
            points = points_obj.points if points_obj else 0
        elif task.status in [Task.Status.TO_DO.value, Task.Status.STARTED.value]:
            try:
                preference = Preference.objects.get(user=task.user, subject=task.subject)
                points = preference.difficulty * 10
            except Preference.DoesNotExist:
                points = 0
        else:
            points = 0

        context['points'] = points
        context['is_parent_of_task_user'] = is_parent_of_task_user
        context['child_id'] = task.user.id if is_parent_of_task_user else None

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

class StartTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.status = Task.Status.STARTED.value
        task.started_at = now()
        task.save(update_fields=['status', 'started_at'])
        return JsonResponse({'minutes': task.time})

@method_decorator(csrf_exempt, name='dispatch')
class PauseTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        try:
            data = json.loads(request.body)
            rem = int(data.get('remaining_minutes'))
        except (ValueError, KeyError):
            return JsonResponse({'error': 'Invalid payload'}, status=400)

        task.time = rem
        task.save(update_fields=['time'])
        return HttpResponse(status=204)

class FinishEarlyTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        parent = request.user.parent
        if not parent:
            return JsonResponse({'error': _('Parent not found')}, status=403)

        try:
            data = json.loads(request.body)
            password = data.get('password')
        except (ValueError, KeyError):
            return JsonResponse({'error': 'Invalid payload'}, status=400)

        user = authenticate(username=parent.username, password=password)
        if not user:
            return JsonResponse({'error': _('Invalid password')}, status=403)

        task.status = Task.Status.DONE.value
        task.finished_at = now()
        task.save(update_fields=['status', 'finished_at'])

        try:
            pref = Preference.objects.get(user=request.user, subject=task.subject)
            if (
                    task.due_date
                    and task.started_at
                    and task.finished_at
                    and task.started_at.date() <= task.due_date <= task.finished_at.date()
            ):
                points_awarded = max(0, (pref.difficulty * 10) - 5)
            else:
                points_awarded = pref.difficulty * 10
        except Preference.DoesNotExist:
            points_awarded = 0

        Points.objects.create(
            user=request.user,
            task=task,
            subject=task.subject,
            points=points_awarded,
        )
        return JsonResponse({'awarded': points_awarded})

class FinishTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.status = Task.Status.DONE.value
        task.finished_at = now()
        task.save(update_fields=['status', 'finished_at'])

        try:
            pref = Preference.objects.get(user=request.user, subject=task.subject)
            if (
                    task.due_date
                    and task.started_at
                    and task.finished_at
                    and task.started_at.date() <= task.due_date <= task.finished_at.date()
            ):
                points_awarded = max(0, (pref.difficulty * 10) - 5)
            else:
                points_awarded = pref.difficulty * 10
        except Preference.DoesNotExist:
            points_awarded = 0

        Points.objects.create(
            user=request.user,
            task=task,
            subject=task.subject,
            points=points_awarded,
        )

        return JsonResponse({'awarded': points_awarded})