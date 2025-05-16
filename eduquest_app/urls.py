from django.urls import path
from .views import index, LoginView, LogoutView, SignUpView, ProfileView, ChildUserCreationView, \
    ChildFirstLoginView, SetPreferencesView, manage_parent_profile, manage_child_profile, \
    EmailUpdateView, DeleteChildProfileView, DeleteParentProfileView, \
    ParentUsernameUpdateView, ChildUsernameUpdateView, ParentPasswordUpdateView, \
    ChildPasswordUpdateView, PreferencesUpdateView, TasksListView, TaskCreateView, TaskEditView, TaskDeleteView, \
    TaskDetailView, RewardCreateView, RewardDeleteView, RewardEditView, StartTaskView, FinishTaskView, RewardClaimView, \
    PauseTaskView, FinishEarlyTaskView

urlpatterns = [
    path('', index, name='index'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('add-child-user/', ChildUserCreationView.as_view(), name='add-child-user'),
    path('login/', LoginView.as_view(), name='login'),
    path('child-first-login/', ChildFirstLoginView.as_view(), name='child-first-login'),
    path('set-preference/<int:child_id>/', SetPreferencesView.as_view(), name='set-preference'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('manage-parent-profile/', manage_parent_profile, name='manage-parent-profile'),
    path('manage-child-profile/<int:child_id>/', manage_child_profile, name='manage-child-profile'),
    path('email-update/', EmailUpdateView.as_view(), name='email-update'),
    path('username-update/', ParentUsernameUpdateView.as_view(), name='parent-username-update'),
    path('child/<int:child_id>/username-update/', ChildUsernameUpdateView.as_view(), name='child-username-update'),
    path('password-update/', ParentPasswordUpdateView.as_view(), name='parent-password-update'),
    path('child/<int:child_id>/password-update/', ChildPasswordUpdateView.as_view(), name='child-password-update'),
    path('delete-parent-profile-confirmation', DeleteParentProfileView.as_view(), name='delete-parent-profile-confirmation'),
    path('delete-child-profile-confirmation/<int:child_id>/', DeleteChildProfileView.as_view(), name='delete-child-profile-confirmation'),
    path('child/<int:child_id>/preferences-update/', PreferencesUpdateView.as_view(), name='preferences-update'),
    path('reward-create/<int:child_id>/', RewardCreateView.as_view(), name='reward-create'),
    path('child/<int:child_id>/reward-edit/<int:pk>/', RewardEditView.as_view(), name='reward-edit'),
    path('reward-delete/<int:child_id>/<int:pk>/', RewardDeleteView.as_view(), name='reward-delete'),
    path('child/<int:child_id>/reward/<int:reward_id>/claim/', RewardClaimView.as_view(),name='reward-claim'),
    path('tasks/', TasksListView.as_view(), name='tasks'),
    path('tasks/<int:pk>/',TaskDetailView.as_view(), name='task-detail'),
    path('tasks/create/', TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/edit/', TaskEditView.as_view(), name='task-edit'),
    path('tasks/<int:pk>/delete/', TaskDeleteView.as_view(), name='task-delete'),
    path('tasks/<int:pk>/start/', StartTaskView.as_view(), name='task-start'),
    path('tasks/<int:pk>/pause/', PauseTaskView.as_view(), name='task-pause'),
    path('tasks/<int:pk>/finish-early/', FinishEarlyTaskView.as_view(), name='task-finish-early'),
    path('tasks/<int:pk>/finish/', FinishTaskView.as_view(), name='task-finish'),
]