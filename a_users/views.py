from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages
from django.contrib.sites.models import Site
from django.http import Http404
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import *
from django.db.models import Q
from .models import Profile,  FriendList, FriendRequest, BlockedUser

@login_required(login_url='/accounts/login/')
def profile_page(request):
    user = request.user
    # Kiểm tra nếu user chưa có profile, tạo mới
    profile, created = Profile.objects.get_or_create(user=user)
    if not profile.realname or not profile.avatar:
        return redirect('profile-edit')
    else:
        return render(request, 'a_users/profile.html', {'profile': profile})

@login_required(login_url='/accounts/login/')
def profile_edit_page(request):
    form = ProfileForm(instance=request.user.profile)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            
    # if request.path == reverse('profile-onboarding'):
    #     template = 'a_users/profile_onboarding.html'
    # else:
    #     template = 'a_users/profile_edit.html'
    template = 'a_users/edit_profile.html'
         
    return render(request, template, {'form':form})

@login_required
@require_POST
def send_friend_request(request, user_id):
    """
    Gửi lời mời kết bạn đến một người dùng cụ thể
    """
    receiver = get_object_or_404(User, id=user_id)
    
    # Kiểm tra xem người nhận có phải là người dùng hiện tại không
    if receiver == request.user:
        messages.error(request, "Bạn không thể gửi lời mời kết bạn cho chính mình!")
        return redirect('user_profile', user_id=user_id)
    
    # Kiểm tra xem người dùng có bị chặn không
    if BlockedUser.objects.filter(user=request.user, blocked_user=receiver).exists():
        messages.error(request, "Bạn đã chặn người dùng này. Vui lòng bỏ chặn trước khi gửi lời mời kết bạn.")
        return redirect('user_profile', user_id=user_id)
    
    if BlockedUser.objects.filter(user=receiver, blocked_user=request.user).exists():
        messages.error(request, "Bạn không thể gửi lời mời kết bạn cho người dùng này.")
        return redirect('user_profile', user_id=user_id)
    
    # Kiểm tra xem đã là bạn bè chưa
    try:
        friend_list = FriendList.objects.get(user=request.user)
        if receiver in friend_list.friends.all():
            messages.info(request, "Người dùng này đã là bạn bè của bạn.")
            return redirect('user_profile', user_id=user_id)
    except FriendList.DoesNotExist:
        pass
    
    # Kiểm tra xem đã gửi lời mời kết bạn trước đó chưa
    if FriendRequest.objects.filter(sender=request.user, receiver=receiver, is_active=True).exists():
        messages.info(request, "Bạn đã gửi lời mời kết bạn cho người dùng này.")
        return redirect('user_profile', user_id=user_id)
    
    # Kiểm tra xem có lời mời ngược từ người nhận không
    pending_request = FriendRequest.objects.filter(sender=receiver, receiver=request.user, is_active=True).first()
    if pending_request:
        # Nếu có, tự động chấp nhận lời mời đó thay vì tạo lời mời mới
        pending_request.accept()
        messages.success(request, f"Đã chấp nhận lời mời kết bạn từ {receiver.username}.")
        return redirect('user_profile', user_id=user_id)
    
    # Tạo lời mời kết bạn mới
    friend_request = FriendRequest(sender=request.user, receiver=receiver)
    friend_request.save()
    
    messages.success(request, f"Đã gửi lời mời kết bạn đến {receiver.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã gửi lời mời kết bạn đến {receiver.username}."})
    
    return redirect('user_profile', user_id=user_id)


@login_required
@require_POST
def accept_friend_request(request, user_id):  # Thay đổi tham số từ request_id thành user_id
    """
    Chấp nhận lời mời kết bạn từ một người dùng cụ thể
    """
    sender = get_object_or_404(User, id=user_id)
    friend_request = get_object_or_404(
        FriendRequest, 
        sender=sender, 
        receiver=request.user, 
        is_active=True
    )
    
    # Chấp nhận lời mời và cập nhật danh sách bạn bè
    friend_request.accept()
    
    messages.success(request, f"Đã chấp nhận lời mời kết bạn từ {friend_request.sender.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã chấp nhận lời mời kết bạn từ {friend_request.sender.username}."})
    
    # Chuyển hướng đến danh sách bạn bè hoặc trang cá nhân của người gửi
    return redirect('pending_requests')

@login_required
@require_POST
def decline_friend_request(request, user_id):
    """
    Từ chối lời mời kết bạn
    """
    friend_request = get_object_or_404(FriendRequest, id=user_id, receiver=request.user, is_active=True)
    
    # Từ chối lời mời kết bạn
    friend_request.decline()
    
    messages.info(request, f"Đã từ chối lời mời kết bạn từ {friend_request.sender.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã từ chối lời mời kết bạn từ {friend_request.sender.username}."})
    
    return redirect('pending_requests')


@login_required
@require_POST
def cancel_friend_request(request, user_id):
    """
    Hủy lời mời kết bạn đã gửi trước đó
    """
    user_to_cancel = get_object_or_404(User, id=user_id)
    
    friend_request = get_object_or_404(
        FriendRequest,
        sender=request.user,
        receiver=user_to_cancel,
        is_active=True
    )
    
    # Hủy lời mời kết bạn
    friend_request.cancel()
    
    messages.info(request, f"Đã hủy lời mời kết bạn đến {user_to_cancel.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã hủy lời mời kết bạn đến {user_to_cancel.username}."})
    
    return redirect('user_profile', user_id=user_id)


# khong can vi da bi trung unfriend
@login_required
@require_POST
def remove_friend(request, user_id):
    """
    Xóa bạn bè khỏi danh sách bạn bè
    """
    user_to_remove = get_object_or_404(User, id=user_id)
    
    try:
        friend_list = FriendList.objects.get(user=request.user)
        # Kiểm tra xem có phải bạn bè không
        if user_to_remove in friend_list.friends.all():
            friend_list.unfriend(user_to_remove)
            messages.info(request, f"Đã xóa {user_to_remove.username} khỏi danh sách bạn bè.")
        else:
            messages.error(request, "Người dùng này không phải là bạn bè của bạn.")
    except FriendList.DoesNotExist:
        messages.error(request, "Bạn chưa có danh sách bạn bè.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã xóa {user_to_remove.username} khỏi danh sách bạn bè."})
    
    return redirect('user_profile', user_id=user_id)


@login_required
@require_POST
def block_user(request, user_id):
    """
    Chặn một người dùng
    """
    user_to_block = get_object_or_404(User, id=user_id)
    
    # Không thể chặn chính mình
    if user_to_block == request.user:
        messages.error(request, "Bạn không thể chặn chính mình!")
        return redirect('user_profile', user_id=user_id)
    
    # Kiểm tra xem đã chặn chưa
    if BlockedUser.objects.filter(user=request.user, blocked_user=user_to_block).exists():
        messages.info(request, f"Bạn đã chặn {user_to_block.username} trước đó.")
        return redirect('user_profile', user_id=user_id)
    
    # Xóa các lời mời kết bạn giữa hai người dùng
    FriendRequest.objects.filter(
        (Q(sender=request.user) & Q(receiver=user_to_block)) |
        (Q(sender=user_to_block) & Q(receiver=request.user)),
        is_active=True
    ).update(is_active=False)
    
    # Nếu là bạn bè, xóa khỏi danh sách bạn bè
    try:
        friend_list = FriendList.objects.get(user=request.user)
        if user_to_block in friend_list.friends.all():
            friend_list.unfriend(user_to_block)
    except FriendList.DoesNotExist:
        pass
    
    # Thêm vào danh sách chặn
    blocked_user = BlockedUser(user=request.user, blocked_user=user_to_block)
    blocked_user.save()
    
    messages.success(request, f"Đã chặn {user_to_block.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã chặn {user_to_block.username}."})
    
    return redirect('user_profile', user_id=user_id)

@login_required
@require_POST
def unfriend(request, user_id):
    """
    Xóa bạn bè khỏi danh sách bạn bè
    """
    user_to_unfriend = get_object_or_404(User, id=user_id)
    
    try:
        friend_list = FriendList.objects.get(user=user_id)
        # Kiểm tra xem có phải bạn bè không
        if user_to_unfriend in friend_list.friends.all():
            friend_list.unfriend(user_to_unfriend)
            messages.info(request, f"Đã xóa {user_to_unfriend.username} khỏi danh sách bạn bè.")
        else:
            messages.error(request, "Người dùng này không phải là bạn bè của bạn.")
    except FriendList.DoesNotExist:
        messages.error(request, "Bạn chưa có danh sách bạn bè.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã xóa {user_to_unfriend.username} khỏi danh sách bạn bè."})
    
    return redirect('user_profile', user_id=user_id)

@login_required
@require_POST
def unblock_user(request, user_id):
    """
    Bỏ chặn một người dùng
    """
    user_to_unblock = get_object_or_404(User, id=user_id)
    
    # Tìm và xóa bản ghi chặn
    blocked = BlockedUser.objects.filter(user=request.user, blocked_user=user_to_unblock)
    if blocked.exists():
        blocked.delete()
        messages.success(request, f"Đã bỏ chặn {user_to_unblock.username}.")
    else:
        messages.info(request, f"Bạn chưa chặn {user_to_unblock.username}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': f"Đã bỏ chặn {user_to_unblock.username}."})
    
    return redirect('user_profile', user_id=user_id)

@login_required
def user_list(request):
    """Hiển thị danh sách tất cả người dùng trừ người dùng hiện tại"""
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    # Lấy danh sách ID của những người đã gửi lời mời kết bạn cho người dùng hiện tại
    pending_requests = FriendRequest.objects.filter(
        receiver=request.user, 
        is_active=True
    ).values_list('sender_id', flat=True)
    
    # Lấy danh sách ID của những người mà người dùng hiện tại đã gửi lời mời kết bạn
    sent_requests = FriendRequest.objects.filter(
        sender=request.user, 
        is_active=True
    ).values_list('receiver_id', flat=True)
    
    # Lấy danh sách bạn bè
    try:
        friend_list = FriendList.objects.get(user=request.user)
        friend_ids = friend_list.friends.values_list('id', flat=True)
    except FriendList.DoesNotExist:
        friend_ids = []
    
    # Lấy danh sách ID người dùng đã bị chặn
    blocked = BlockedUser.objects.filter(
        user=request.user
    ).values_list('blocked_user_id', flat=True)
    
    context = {
        'users': users,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'friend_ids': friend_ids,
        'blocked': blocked,
    }
    
    return render(request, 'a_users/user_list.html', context)


@login_required
def search_users(request):
    """Tìm kiếm người dùng theo tên hoặc username"""
    query = request.GET.get('q', '')
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(profile__realname__icontains=query)
        ).exclude(id=request.user.id).select_related('profile')
    else:
        users = User.objects.none()
    
    # Lấy danh sách ID của những người đã gửi lời mời kết bạn cho người dùng hiện tại
    pending_requests = FriendRequest.objects.filter(
        receiver=request.user, 
        is_active=True
    ).values_list('sender_id', flat=True)
    
    # Lấy danh sách ID của những người mà người dùng hiện tại đã gửi lời mời kết bạn
    sent_requests = FriendRequest.objects.filter(
        sender=request.user, 
        is_active=True
    ).values_list('receiver_id', flat=True)
    
    # Lấy danh sách bạn bè
    try:
        friend_list = FriendList.objects.get(user=request.user)
        friend_ids = friend_list.friends.values_list('id', flat=True)
    except FriendList.DoesNotExist:
        friend_ids = []
    
    # Lấy danh sách ID người dùng đã bị chặn
    blocked = BlockedUser.objects.filter(
        user=request.user
    ).values_list('blocked_user_id', flat=True)
    
    context = {
        'users': users,
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'friend_ids': friend_ids,
        'blocked': blocked,
        'query': query,
    }
    
    return render(request, 'a_users/user_list.html', context)


@login_required
def user_profile(request, user_id):
    """Hiển thị trang profile của một người dùng cụ thể"""
    user = get_object_or_404(User, id=user_id)
    
    # Kiểm tra mối quan hệ với người dùng hiện tại
    is_friend = False
    is_pending = False
    is_blocked = False
    request_sent = False
    friendship_status = None
    
    # Kiểm tra xem có phải bạn bè không
    try:
        friend_list = FriendList.objects.get(user=request.user)
        is_friend = user in friend_list.friends.all()
    except FriendList.DoesNotExist:
        pass
    
    # Kiểm tra xem có lời mời kết bạn đang chờ không
    request_received = FriendRequest.objects.filter(
        sender=user,
        receiver=request.user,
        is_active=True
    ).exists()
    
    if request_received:
        is_pending = True
        friendship_status = 'pending'
    
    # Kiểm tra xem đã gửi lời mời kết bạn chưa
    request_sent_obj = FriendRequest.objects.filter(
        sender=request.user,
        receiver=user,
        is_active=True
    ).exists()
    
    if request_sent_obj:
        request_sent = True
        friendship_status = 'pending'
    
    # Kiểm tra xem có bị chặn không
    is_blocked = BlockedUser.objects.filter(
        user=request.user,
        blocked_user=user
    ).exists()
    
    if is_blocked:
        friendship_status = 'blocked'
    elif is_friend:
        friendship_status = 'accepted'
    
    context = {
        'profile_user': user,
        'is_friend': is_friend,
        'is_pending': is_pending,
        'request_sent': request_sent,
        'is_blocked': is_blocked,
        'friendship_status': friendship_status,
    }
    
    return render(request, 'a_users/user_profile.html', context)


@login_required
def friend_list(request):
    """Hiển thị danh sách bạn bè của người dùng hiện tại"""
    try:
        friend_list_obj = FriendList.objects.get(user=request.user)
        friends = friend_list_obj.friends.all().select_related('profile')
    except FriendList.DoesNotExist:
        friends = []
    
    context = {
        'friends': friends,
    }
    
    return render(request, 'a_users/friend_list.html', context)


@login_required
def pending_requests(request):
    """Hiển thị các lời mời kết bạn đang chờ xử lý"""
    pending = FriendRequest.objects.filter(
        receiver=request.user,
        is_active=True
    ).select_related('sender__profile')
    
    context = {
        'pending_requests': pending,
    }

    return render(request, 'a_users/pending_requests.html', context)
