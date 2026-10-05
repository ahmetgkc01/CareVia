from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssistantMessage
from .permissions import IsAssistantUser
from .serializers import AssistantMessageSerializer, AssistantRequestSerializer
from .services import create_reply
from .throttles import AssistantRateThrottle


class AssistantMessageView(APIView):
    permission_classes = (IsAssistantUser,)
    throttle_classes = (AssistantRateThrottle,)

    @extend_schema(responses={200: AssistantMessageSerializer(many=True)})
    def get(self, request):
        messages = list(
            AssistantMessage.objects.filter(user=request.user).order_by("-created_at", "-id")[:100]
        )
        messages.reverse()
        return Response(AssistantMessageSerializer(messages, many=True).data)

    @transaction.atomic
    @extend_schema(
        request=AssistantRequestSerializer,
        responses={201: AssistantMessageSerializer},
    )
    def post(self, request):
        serializer = AssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        AssistantMessage.objects.create(
            user=request.user,
            role=AssistantMessage.Role.USER,
            content=data["message"],
            category="input",
        )
        reply = create_reply(
            request.user,
            data["message"],
            data["language"],
            data.get("patient_id"),
        )
        assistant_message = AssistantMessage.objects.create(
            user=request.user,
            role=AssistantMessage.Role.ASSISTANT,
            content=reply.content,
            category=reply.category,
            safety_code=reply.safety_code,
            sources=reply.sources,
        )
        return Response(
            AssistantMessageSerializer(assistant_message).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request):
        AssistantMessage.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
