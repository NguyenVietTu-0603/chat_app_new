"""
URL configuration for a_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from a_post.views import *
from a_users.views import *
from a_rtchat.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home_page, name='home'),
    path('post/create/', post_create_page, name='post-create'),
    path('post/delete/<uuid:pk>/', post_delete_page, name='post_delete'),
    
    path('accounts/profile/', profile_page, name='profile'),
    path('profile/edit', profile_edit_page, name='profile-edit'),
    
    path('friends/send/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:user_id>/', accept_friend_request, name='accept_friend_request'),
    path('friends/decline/<int:request_id>/', decline_friend_request, name='decline_friend_request'),
    path('friends/cancel/<int:request_id>/', cancel_friend_request, name='cancel_friend_request'),
    path('friends/remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('users/block/<int:user_id>/', block_user, name='block_user'),
    path('users/unblock/<int:user_id>/', unblock_user, name='unblock_user'),
    
    path('chatroom/<str:group_name>/', chat_view, name='chatroom'),
    path('listroom/', list_room_view, name='listroom'),
    path('listroom-private/', private_chat_list, name='listroom_private'),
    path('private-chat/<str:username>/', private_chat_room, name='private_chat_room'),
    
    path('users/user_list/', user_list, name='user_list'),
    path('users/user_list/<int:user_id>/', user_profile, name='user_profile'),   
    path('users/search_users', search_users, name='search_users'),   
    path('users/friend_list', friend_list, name='friend_list'),   
    path('users/pending_requests', pending_requests, name='pending_requests'), 
    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
