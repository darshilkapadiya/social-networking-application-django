from django.urls import path
from .views import SignupView, LoginView, UserSearchView, FriendRequestView, ListFriendsView, ListPendingRequestsView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('search/', UserSearchView.as_view(), name='user-search'),
    path('friend-request/<str:action>/', FriendRequestView.as_view(), name='friend-request'),
    path('friends/', ListFriendsView.as_view(), name='list-friends'),
    path('pending-requests/', ListPendingRequestsView.as_view(), name='pending-requests'),
]
