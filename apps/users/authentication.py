from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

# Clase de autenticación JWT personalizada que extiende JWTAuthentication
class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            # Obtener el encabezado del token
            header = self.get_header(request)

            # Si no hay encabezado, intenta obtener el token de las cookies
            if header is None:
                raw_token = request.COOKIES.get(settings.AUTH_COOKIE)
            else:
                # Si hay encabezado, obtén el token directamente del encabezado
                raw_token = self.get_raw_token(header)

            # Si no hay token, devuelve None
            if raw_token is None:
                return None

            # Validar el token y obtener el token validado
            validated_token = self.get_validated_token(raw_token)

            # Obtener el usuario asociado con el token y devolver el usuario y el token validado
            return self.get_user(validated_token), validated_token
        except:
            # En caso de cualquier excepción, devuelve None
            return None

# Esta clase personalizada de autenticación JWT se encarga de manejar la autenticación basada en tokens JWT en Django. 
# Extiende la funcionalidad de JWTAuthentication proporcionando una implementación personalizada del método authenticate. 
# En este método:

# Intenta obtener el token de autenticación de las cookies (request.COOKIES) si no se proporciona en el encabezado de 
# la solicitud.
# Si se proporciona en el encabezado, obtiene el token directamente del encabezado.
# Luego, valida el token y obtiene el token validado.
# Finalmente, obtiene el usuario asociado con el token y devuelve una tupla de usuario y token validado.
# Si hay alguna excepción durante este proceso, la función retorna None. Esto podría suceder si el token no es 
# válido o si hay algún problema en el proceso de autenticación.