from django.urls import path, re_path
from .consumers import ChatroomConsumer, PrivateChatConsumer

websocket_urlpatterns = [
    path("ws/chatroom/<chatroom_name>/", ChatroomConsumer.as_asgi()),
    re_path(r"ws/private-chat/(?P<other_username>\w+)/$", PrivateChatConsumer.as_asgi()),
]
