import hashlib
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponse


class ThrottledLogin(LoginView):
    template_name = "registration/login.html"

    def post(self, request, *args, **kwargs):
        raw = (
            request.META.get("REMOTE_ADDR", "") + "|" + request.POST.get("username", "")
        )
        self.limit_key = "login:" + hashlib.sha256(raw.encode()).hexdigest()
        if cache.get(self.limit_key, 0) >= 10:
            return HttpResponse("Demasiados intentos. Espera 10 minutos.", status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        cache.set(self.limit_key, cache.get(self.limit_key, 0) + 1, 600)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.limit_key)
        return super().form_valid(form)
