from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile
from matches.models import Team

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name"]

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    preferred_teams = TeamSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            "user",
            "nama_lengkap",
            "nomor_telepon",
            "preferred_teams",
        ]

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["nama_lengkap", "nomor_telepon"]

class PreferredTeamsUpdateSerializer(serializers.Serializer):
    team_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )
