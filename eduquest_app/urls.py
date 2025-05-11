from django.urls import path
from .views import index, LoginView, LogoutView, SignUpView, ProfileView, ChildUserCreationView, TasksView, \
    ChildFirstLoginView, SetPreferencesView, manage_parent_profile, edit_parent_profile, manage_child_profile, \
    edit_child_profile, delete_child_profile, delete_parent_profile

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
    path('edit-parent-profile/', edit_parent_profile, name='edit-parent-profile'),
    path('parent/delete/', delete_parent_profile, name='delete-parent-profile-confirmation'),
    path('manage-child-profile/<int:child_id>/', manage_child_profile, name='manage-child-profile'),
    path('child/<int:child_id>/edit/', edit_child_profile, name='edit-child-profile'),
    path('child/<int:child_id>/delete/', delete_child_profile, name='delete-child-profile-confirmation'),
    path('tasks/', TasksView.as_view(), name='tasks'),
]