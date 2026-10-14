from django.contrib import admin
from django.contrib.auth.views import (
    LogoutView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.urls import path
from django.conf import settings
from django.views.static import serve
from p2p import views
from p2p.auth import ThrottledLogin

urlpatterns = [
    path("health/", views.health),
    path("login/", ThrottledLogin.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "password/",
        PasswordChangeView.as_view(template_name="registration/password_change.html"),
        name="password_change",
    ),
    path(
        "password/done/",
        PasswordChangeDoneView.as_view(template_name="registration/password_done.html"),
        name="password_change_done",
    ),
    path("admin/", admin.site.urls),
    path("", views.page),
    path("usd-airtm", views.page, {"kind": "usd-airtm"}),
    path("ordenes", views.page, {"kind": "orders"}),
    path("inventario", views.page, {"kind": "inventory"}),
    path("operadores", views.page, {"kind": "management"}),
    path("api/context", views.context),
    path("api/operators", views.operators_api),
    path("api/users", views.users_api),
    path("api/accounts", views.accounts_api),
    path("api/orders", views.orders_api),
    path("api/orders/backup", views.orders_api, {"backup": True}),
    path("api/orders/<uuid:pk>", views.orders_api),
    path("api/orders/<uuid:pk>/receipt", views.orders_api, {"receipt": True}),
    path("api/inventory", views.inventory_api),
    path("api/withdrawals", views.movements_api),
    path("api/withdrawals/<uuid:pk>", views.movements_api),
    path("api/profits", views.profits_api),
    path("api/report", views.report_api),
    path("api/import", views.import_api),
    path("api/audit", views.audit_api),
    path("api/calculate", views.calculate_api),
    path("api/advertiser", views.advertiser_api),
    path("api/own-ads", views.own_ads_api),
    path("api/notification-state", views.notification_state_api),
    path("api/<str:kind>", views.market_api),
]
if settings.DEBUG:
    urlpatterns += [
        path(
            "static/<path:path>", serve, {"document_root": settings.BASE_DIR / "static"}
        )
    ]
