from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.auditlog.services import record_event

from .models import User
from .permissions import UserManagementPermission
from .serializers import (
    CurrentUserSerializer,
    DetailSerializer,
    LoginSerializer,
    UserManagementSerializer,
)
from .throttles import LoginRateThrottle


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(responses={200: DetailSerializer})
    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)

    @extend_schema(request=LoginSerializer, responses={200: CurrentUserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            record_event(
                request,
                action="login_failed",
                status_code=status.HTTP_400_BAD_REQUEST,
                username=serializer.validated_data["username"],
            )
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        record_event(request, action="login", status_code=status.HTTP_200_OK, user=user)
        return Response(CurrentUserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        record_event(
            request,
            action="logout",
            status_code=status.HTTP_204_NO_CONTENT,
            user=request.user,
        )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: CurrentUserSerializer})
    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class UserViewSet(ModelViewSet):
    serializer_class = UserManagementSerializer
    permission_classes = (UserManagementPermission,)
    filterset_fields = ("is_active", "groups__name")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering_fields = ("username", "first_name", "last_name", "date_joined")

    def get_queryset(self):
        return (
            User.objects.prefetch_related("groups")
            .filter(is_superuser=False)
            .order_by("last_name", "first_name", "username")
            .distinct()
        )


