import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import ChatGroup, GroupMessage, PrivateMessage, PrivateChat
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

class ChatroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = self.scope['url_route']['kwargs']['chatroom_name']
        self.room_group_name = f'chat_{self.group_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']

        user = await sync_to_async(User.objects.get)(username=username)
        group = await sync_to_async(ChatGroup.objects.get)(group_name=self.group_name)
        new_message = await sync_to_async(GroupMessage.objects.create)(
            group=group, author=user, body=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username
            }
        )

    async def chat_message(self, event):
        message = event['message']
        username = event['username']

        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.other_username = self.scope["url_route"]["kwargs"]["other_username"].split("_", 1)[1]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"private_chat_{min(self.user.username, self.other_username)}_{max(self.user.username, self.other_username)}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        msg_type = data.get("type", "text")
        message = data.get("message", "")
        file_url = ""
        is_image = False

        sender = self.user
        receiver = await self.get_user(self.other_username)

        if msg_type in ["image", "file"]:
            raw_data = data.get("data", "")
            filename = data.get("filename", "file")

            if raw_data:
                format, base64_data = raw_data.split(";base64,", 1)
                decoded_file = ContentFile(base64.b64decode(base64_data), name=filename)

                file_path = f"private_chat_files/{filename}"
                saved_path = default_storage.save(file_path, decoded_file)
                file_url = f"/private_chat_files/{filename}"  

                try:
                    from PIL import Image
                    with default_storage.open(saved_path, 'rb') as f:
                        img = Image.open(f)
                        img.verify()
                    is_image = True
                    msg_type = "image"
                except Exception:
                    is_image = False
                    msg_type = "file"

        if receiver:
            chat = await self.get_or_create_private_chat(sender, receiver)

            new_message = await self.save_message(chat, sender, message, file_url if msg_type != "text" else None, is_image)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": sender.username,
                    "realname": await sync_to_async(lambda: sender.profile.realname)(),
                    "message": message,
                    "file_url": file_url,
                    "msg_type": msg_type,
                    "filename": data.get("filename", "") if msg_type != "text" else "",
                    "timestamp": str(new_message.created),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @staticmethod
    async def get_user(username):
        try:
            return await sync_to_async(User.objects.get)(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def get_or_create_private_chat(user1, user2):
        chat, created = await sync_to_async(PrivateChat.objects.get_or_create)(
            user1=max(user1, user2, key=lambda u: u.username),
            user2=min(user1, user2, key=lambda u: u.username),
        )
        return chat

    @staticmethod
    async def save_message(chat, sender, message, file_url=None, is_image=False):
        new_message = await sync_to_async(PrivateMessage.objects.create)(
            chat=chat,
            sender=sender,
            body=message,
            file=file_url if file_url else None,
            is_image=is_image if file_url else False,
        )
        return new_message