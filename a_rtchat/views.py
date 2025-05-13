from django.shortcuts import render, get_object_or_404
from .models import ChatGroup, GroupMessage,PrivateChat, PrivateMessage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Max
import time
from agora_token_builder import RtcTokenBuilder

@login_required(login_url='/accounts/login/')
def chat_view(request, group_name):
    chat_group = get_object_or_404(ChatGroup, group_name=group_name)
    chat_messages = chat_group.chat_messages.all().order_by('created')

    return render(request, 'a_rtchat/chat.html', {  # Đảm bảo đường dẫn đúng
        'chat_group': chat_group,
        'chat_messages': chat_messages,
    })

@login_required(login_url='/accounts/login/')
def list_room_view(request):
    list_room = ChatGroup.objects.all()
    return render(request, 'a_rtchat/list_room.html', {'list_room' : list_room})

@login_required
def private_chat_list(request):
    """Hiển thị danh sách các cuộc trò chuyện riêng tư của người dùng hiện tại"""
    chats = PrivateChat.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    return render(request, 'a_rtchat/private_chat_list.html', {'chats': chats})


@login_required
def private_chat_room(request, username):
    """Mở phòng chat riêng tư với một người dùng khác"""
    # Lấy thông tin người dùng khác
    other_user = get_object_or_404(User, username=username)
    
    # Sắp xếp user1 và user2 theo id để đảm bảo không tạo trùng lặp
    chat, created = PrivateChat.objects.get_or_create(
        user1=request.user if request.user.id < other_user.id else other_user,
        user2=request.user if request.user.id > other_user.id else other_user
    )

    # Lấy tất cả tin nhắn trong phòng chat, sắp xếp theo thời gian
    messages = chat.messages.all().order_by('created')

    # Lấy tin nhắn cuối cùng
    last_message = messages.last()

     # Annotate thời gian tin nhắn gần nhất cho từng cuộc trò chuyện
    chats = PrivateChat.objects.filter(Q(user1=request.user) | Q(user2=request.user)) \
        .annotate(last_msg_time=Max('messages__created')) \
        .order_by('-last_msg_time')
    
    # Truyền dữ liệu vào template
    return render(request, 'a_rtchat/private_chat.html', {
        'chat': chat,
        'messages': messages,
        'last_message': last_message,
        'other_user': other_user,
        'users': chats,
    })

def generate_agora_token(request):
    app_id = "7cb464ea47294418a5ec225bc89b0c11"
    app_certificate = "68a0d5c4bec64b81843b76b134c2f554"
    channel_name = "test_channel"
    uid = request.user.id
    expiration_time_in_seconds = 3600
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expiration_time_in_seconds

    token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_name, uid, 1, privilege_expired_ts)
    return JsonResponse({'token': token})