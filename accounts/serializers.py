"""Validacion de credenciales y registro sin campos de privilegios."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from web.api import StrictInputMixin

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="effective_role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role"]
        read_only_fields = fields


class LoginSerializer(StrictInputMixin, serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class RegistrationSerializer(StrictInputMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "password_confirmation"]
        extra_kwargs = {"first_name": {"required": True, "allow_blank": False}, "last_name": {"required": True, "allow_blank": False}}

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya esta ocupado.")
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya tiene una cuenta.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmation"):
            raise serializers.ValidationError({"password_confirmation": "Las contrasenas no coinciden."})
        user = User(**{key: value for key, value in attrs.items() if key != "password"})
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.SPECTATOR)
