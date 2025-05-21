from django.urls import path, re_path
from .consumers import ChatroomConsumer, PrivateChatConsumer
from . import consumers

websocket_urlpatterns = [
    path("ws/chatroom/<chatroom_name>/", consumers.ChatroomConsumer.as_asgi()),
    re_path(r"ws/private-chat/(?P<other_username>\w+)/$", consumers.PrivateChatConsumer.as_asgi()),
    re_path(r'ws/video-call/(?P<username>\w+)/$', consumers.VideoCallConsumer.as_asgi()),
]
