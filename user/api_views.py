from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile
from .api_serializers import (
    UserSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    PreferredTeamsUpdateSerializer
)
from matches.models import Team


# =====================
# REGISTER USER
# =====================
class RegisterAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "Username & password wajib"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username sudah digunakan"}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        return Response({"detail": "Akun berhasil dibuat"}, status=201)


# =====================
# LOGIN (JWT)
# =====================
class LoginAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "Username atau password salah"}, status=400)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


# =====================
# LOGOUT
# =====================
class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout berhasil"})
        except:
            return Response({"detail": "Token tidak valid"}, status=400)


# =====================
# GET PROFILE
# =====================
class GetProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)


# =====================
# UPDATE PROFILE
# =====================
class UpdateProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile = request.user.profile
        serializer = ProfileUpdateSerializer(instance=profile, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Profil diperbarui"})
        return Response(serializer.errors, status=400)


# =====================
# GET PREFERRED TEAMS
# =====================
class PreferredTeamsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teams = request.user.profile.preferred_teams.all()
        data = [{"id": t.id, "name": t.name} for t in teams]
        return Response(data)


# =====================
# UPDATE PREFERRED TEAMS
# =====================
class UpdatePreferredTeamsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PreferredTeamsUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        team_ids = serializer.validated_data["team_ids"]
        teams = Team.objects.filter(id__in=team_ids)

        profile = request.user.profile
        profile.preferred_teams.set(teams)
        profile.save()

        return Response({"detail": "Preferred teams diperbarui"})
