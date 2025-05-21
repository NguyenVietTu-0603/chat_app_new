from django.contrib.auth.models import User
from .models import FriendList

def friends_context(request):
    if request.user.is_authenticated:
        try:
            # Lấy danh sách bạn bè
            friend_list = FriendList.objects.get(user=request.user)
            friend_ids = friend_list.friends.values_list('id', flat=True)
            users = User.objects.all()
        except FriendList.DoesNotExist:
            friend_ids = []
            users = []
    else:
        friend_ids = []
        users = []

    return {
        'users': users,
        'friend_ids': friend_ids,
    }