from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def video_call_view(request):
    return render(request, 'a_rtchat/video_call.html')
import time
from agora_token_builder import RtcTokenBuilder
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