from django.db.models import Q
from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from .serializers import UserSerializer, FriendRequestSerializer
from .models import FriendRequest
from .utils import custom_response
import time
import re

request_timestamps = {}

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower()
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not email or not password:
            return custom_response("Email and password are required", [], 400)

        if not re.match(EMAIL_REGEX, email):
            return custom_response("Invalid email format", [], 400)

        if User.objects.filter(email=email).exists():
            return custom_response("Email already registered", [], 400)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        return custom_response("User registered successfully", [], 201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').lower()
        password = request.data.get('password')

        if not email or not password:
            return custom_response("Email and password are required", [], 400)

        user = authenticate(username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return custom_response("Login successful", {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, 200)
        else:
            return custom_response("Invalid email or password", [], 401)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keyword = request.GET.get('q', '')
        if '@' in keyword:
            users = User.objects.filter(email__iexact=keyword)
        else:
            users = User.objects.filter(
                Q(first_name__icontains=keyword) | 
                Q(last_name__icontains=keyword)
            )
        
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        serializer = UserSerializer(page_obj.object_list, many=True)
        return custom_response("Users retrieved successfully", serializer.data, 200)


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, action):
        sender = request.user
        receiver_id = request.data.get('receiver_id')

        if not receiver_id:
            return custom_response("Receiver must be specified", [], 400)
        
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return custom_response("Receiver does not exist", [], 404)

        try:
            if action == 'send':
                current_time = time.time()
                if sender.id not in request_timestamps:
                    request_timestamps[sender.id] = []

                request_timestamps[sender.id] = [timestamp for timestamp in request_timestamps[sender.id] if current_time - timestamp < 60]

                if len(request_timestamps[sender.id]) >= 3:
                    return custom_response("Rate limit exceeded. Try again later.", [], 429)

                request_timestamps[sender.id].append(current_time)

                friend_request = FriendRequest(sender=sender, receiver=receiver)
                friend_request.save()
                return custom_response("Friend request sent", {"friend_request_id": friend_request.id}, 201)

            elif action == 'accept':
                friend_request = FriendRequest.objects.get(sender=receiver, receiver=sender, accepted=False)
                friend_request.accepted = True
                friend_request.save()
                return custom_response("Friend request accepted", [], 200)

            elif action == 'reject':
                friend_request = FriendRequest.objects.get(sender=receiver, receiver=sender, accepted=False)
                friend_request.delete()
                return custom_response("Friend request rejected", [], 200)

            else:
                return custom_response("Invalid action", [], 400)

        except FriendRequest.DoesNotExist:
            return custom_response("Friend request does not exist", [], 404)
        except ValidationError as e:
            return custom_response(f"Validation error: {e.message}", [], 400)
        except Exception as e:
            return custom_response(f"Error: {str(e)}", [], 500)


class ListFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        friends = User.objects.filter(
            Q(sent_requests__receiver=user, sent_requests__accepted=True) |
            Q(received_requests__sender=user, received_requests__accepted=True)
        ).distinct()

        serializer = UserSerializer(friends, many=True)
        return custom_response("Friends list retrieved successfully", serializer.data, 200)


class ListPendingRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        pending_requests = FriendRequest.objects.filter(receiver=user, accepted=False)

        serializer = FriendRequestSerializer(pending_requests, many=True)
        return custom_response("Pending friend requests retrieved successfully", serializer.data, 200)
