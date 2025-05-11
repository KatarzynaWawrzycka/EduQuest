from django.urls import path
from .views import index, LoginView, LogoutView, SignUpView, ProfileView, ChildUserCreationView, TasksView, \
    ChildFirstLoginView, SetPreferencesView

urlpatterns = [
    path('', index, name='index'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('add-child-user/', ChildUserCreationView.as_view(), name='add-child-user'),
    path('login/', LoginView.as_view(), name='login'),
    path('child-first-login/', ChildFirstLoginView.as_view(), name='child-first-login'),
    path('set-preference/<int:child_id>/', SetPreferencesView.as_view(), name='set-preference'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('tasks/', TasksView.as_view(), name='tasks'),
]