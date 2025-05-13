from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', default='avt.jpg', null=True, blank=True) 
    realname = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(unique=True, null=True)
    location = models.CharField(max_length=20, null=True, blank=True)
    bio = models.TextField(null=True, blank=True) 
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return str(self.user)
    
    @property
    def avatar(self):
        try:
            avatar = self.image.url
        except:
            avatar = static('images/avt.jpg')
        return avatar
    
    @property
    def name(self):
        if self.realname:
            name = self.realname
        else:
            name = self.user.username 
        return name
    
class FriendList(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='friend_list')
    friends = models.ManyToManyField(User, blank=True, related_name='friends')
    
    def __str__(self):
        return f"{self.user.username}'s friends"
    
    def add_friend(self, account):
        """
        Thêm một người dùng vào danh sách bạn bè
        """
        if account not in self.friends.all():
            self.friends.add(account)
            self.save()
    
    def remove_friend(self, account):
        """
        Xóa một người dùng khỏi danh sách bạn bè
        """
        if account in self.friends.all():
            self.friends.remove(account)
            self.save()
    
    def unfriend(self, removee):
        """
        Hủy kết bạn với một người dùng (xóa ở cả hai bên)
        """
        # Xóa khỏi danh sách bạn bè của mình
        self.remove_friend(removee)
        # Xóa mình khỏi danh sách bạn bè của họ
        friend_list = FriendList.objects.get(user=removee)
        friend_list.remove_friend(self.user)


class FriendRequest(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    is_active = models.BooleanField(default=True)
    is_declined = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username}"
    
    def accept(self):
        """
        Chấp nhận lời mời kết bạn và cập nhật danh sách bạn bè cho cả hai người dùng
        """
        receiver_friend_list, created = FriendList.objects.get_or_create(user=self.receiver)
        if created:
            receiver_friend_list.save()
        
        sender_friend_list, created = FriendList.objects.get_or_create(user=self.sender)
        if created:
            sender_friend_list.save()
            
        # Thêm vào danh sách bạn bè của nhau
        receiver_friend_list.add_friend(self.sender)
        sender_friend_list.add_friend(self.receiver)
        
        # Đánh dấu lời mời là không còn active
        self.is_active = False
        self.save()
    
    def decline(self):
        """
        Từ chối lời mời kết bạn
        """
        self.is_active = False
        self.is_declined = True
        self.save()
    
    def cancel(self):
        """
        Hủy lời mời kết bạn đã gửi
        """
        self.is_active = False
        self.is_cancelled = True
        self.save()


class BlockedUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_blocks')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'blocked_user']
        
    def __str__(self):
        return f"{self.user.username} blocked {self.blocked_user.username}"