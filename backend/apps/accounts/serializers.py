from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class CurrentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    groups = serializers.SerializerMethodField()

    def get_groups(self, user) -> list[str]:
        return list(user.groups.order_by("name").values_list("name", flat=True))


class UserManagementSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=Group.objects.all(),
    )
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "groups",
            "is_active",
            "last_login",
            "date_joined",
            "password",
        )
        read_only_fields = ("id", "last_login", "date_joined")

    def validate_groups(self, groups):
        request = self.context.get("request")
        assigning_admin = any(group.name == "Admin" for group in groups)
        if assigning_admin and not (request and request.user.is_superuser):
            raise serializers.ValidationError(
                "Only a Super User can assign the Admin role."
            )
        return groups

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        user = User.objects.create_user(password=password, **validated_data)
        user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance

