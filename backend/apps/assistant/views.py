from time import perf_counter

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssistantMessage
from .permissions import IsAssistantUser
from .serializers import AssistantMessageSerializer, AssistantRequestSerializer
from .services import create_reply, resolve_patient
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

        patient = resolve_patient(request.user, data.get("patient_id"))
        history_limit = max(0, settings.ASSISTANT_HISTORY_MESSAGES)
        history_queryset = AssistantMessage.objects.filter(
            user=request.user,
            patient=patient,
        ).order_by("-created_at", "-id")
        history = list(history_queryset[:history_limit]) if history_limit else []
        history.reverse()

        AssistantMessage.objects.create(
            user=request.user,
            patient=patient,
            role=AssistantMessage.Role.USER,
            content=data["message"],
            category="input",
        )
        started_at = perf_counter()
        reply = create_reply(
            request.user,
            data["message"],
            data["language"],
            data.get("patient_id"),
            history,
        )
        latency_ms = max(0, round((perf_counter() - started_at) * 1000))
        assistant_message = AssistantMessage.objects.create(
            user=request.user,
            patient=patient,
            role=AssistantMessage.Role.ASSISTANT,
            content=reply.content,
            category=reply.category,
            safety_code=reply.safety_code,
            sources=reply.sources,
            provider_model=reply.provider_model,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            estimated_cost_usd=reply.estimated_cost_usd,
            latency_ms=latency_ms,
            fallback_used=reply.fallback_used,
        )
        return Response(
            AssistantMessageSerializer(assistant_message).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request):
        AssistantMessage.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
