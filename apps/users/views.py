from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from djoser.social.views import ProviderAuthView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from rest_framework_simplejwt.exceptions import InvalidToken

# Vista personalizada para la autenticación de proveedores (por ejemplo, inicio de sesión social)
class CustomProviderAuthView(ProviderAuthView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if response.status_code == 201:  # Si la autenticación es exitosa
            # Obtener tokens de acceso y actualización
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            if access_token and refresh_token:
                # Configurar cookies con los tokens
                response.set_cookie(
                    'access',
                    access_token,
                    max_age=settings.AUTH_COOKIE_MAX_AGE,
                    path=settings.AUTH_COOKIE_PATH,
                    secure=settings.AUTH_COOKIE_SECURE,
                    httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                    samesite=settings.AUTH_COOKIE_SAMESITE
                )
                response.set_cookie(
                    'refresh',
                    refresh_token,
                    max_age=settings.AUTH_COOKIE_MAX_AGE,
                    path=settings.AUTH_COOKIE_PATH,
                    secure=settings.AUTH_COOKIE_SECURE,
                    httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                    samesite=settings.AUTH_COOKIE_SAMESITE
                )
        else:
            return Response({'detail': 'Autenticación fallida'}, status=response.status_code)

        return response

# Vista personalizada para obtener un par de tokens de acceso y actualización
class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken as e:
            return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        if response.status_code == 200:  # Si la obtención de tokens es exitosa
            # Obtener tokens de acceso y actualización
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')

            if access_token and refresh_token:
                # Configurar cookies con los tokens
                response.set_cookie(
                    'access',
                    access_token,
                    max_age=settings.AUTH_COOKIE_MAX_AGE,
                    path=settings.AUTH_COOKIE_PATH,
                    secure=settings.AUTH_COOKIE_SECURE,
                    httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                    samesite=settings.AUTH_COOKIE_SAMESITE
                )
                response.set_cookie(
                    'refresh',
                    refresh_token,
                    max_age=settings.AUTH_COOKIE_MAX_AGE,
                    path=settings.AUTH_COOKIE_PATH,
                    secure=settings.AUTH_COOKIE_SECURE,
                    httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                    samesite=settings.AUTH_COOKIE_SAMESITE
                )
        else:
            return Response({'detail': 'Error al obtener los tokens'}, status=response.status_code)

        return response

# Vista personalizada para refrescar un token de acceso
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            request.data['refresh'] = refresh_token

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken as e:
            return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        if response.status_code == 200:  # Si el refresco de token es exitoso
            # Obtener un nuevo token de acceso
            access_token = response.data.get('access')

            if access_token:
                # Configurar cookies con el nuevo token de acceso
                response.set_cookie(
                    'access',
                    access_token,
                    max_age=settings.AUTH_COOKIE_MAX_AGE,
                    path=settings.AUTH_COOKIE_PATH,
                    secure=settings.AUTH_COOKIE_SECURE,
                    httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                    samesite=settings.AUTH_COOKIE_SAMESITE
                )
        else:
            return Response({'detail': 'Error al refrescar el token'}, status=response.status_code)

        return response

# Vista personalizada para verificar un token de acceso
class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access')

        if access_token:
            request.data['token'] = access_token

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken as e:
            return Response({'detail': 'Token inválido o expirado'}, status=status.HTTP_401_UNAUTHORIZED)

        return response

# Vista personalizada para cerrar sesión
class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)

        # Eliminar cookies de tokens de acceso y actualización
        response.delete_cookie('access')
        response.delete_cookie('refresh')

        return response
