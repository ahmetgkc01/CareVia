from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.accounts.models import User

from .models import Clinician


class ClinicianSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")
    username = serializers.CharField(source="user.username")
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = Clinician
        fields = (
            "public_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "profession",
            "specialty",
            "country_code",
            "is_active",
        )
        read_only_fields = ("public_id",)

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required."})
        user = User.objects.create_user(password=password, **user_data)
        clinician = Clinician.objects.create(user=user, **validated_data)
        self._sync_group(clinician)
        return clinician

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        password = validated_data.pop("password", None)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        clinician = super().update(instance, validated_data)
        self._sync_group(clinician)
        return clinician

    @staticmethod
    def _sync_group(clinician):
        role_name = "Doctor" if clinician.profession == Clinician.Profession.DOCTOR else "Nurse"
        role, _ = Group.objects.get_or_create(name=role_name)
        clinician.user.groups.remove(*Group.objects.filter(name__in=("Doctor", "Nurse")))
        clinician.user.groups.add(role)


class ClinicianSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Clinician
        fields = ("public_id", "display_name", "profession", "specialty")

