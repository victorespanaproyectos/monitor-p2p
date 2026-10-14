from django.http import JsonResponse
from django.shortcuts import redirect


class AccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not request.user.is_authenticated and not path.startswith(
            ("/login/", "/static/", "/health/")
        ):
            if path.startswith("/api/"):
                return JsonResponse(
                    {"error": "Inicia sesión para continuar."}, status=401
                )
            return redirect("/login/?next=" + path)
        return self.get_response(request)
