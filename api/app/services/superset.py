import httpx

from app.config import get_settings
from app.schemas import SupersetEmbedConfig


async def get_embed_config() -> SupersetEmbedConfig:
    settings = get_settings()
    if not settings.superset_dashboard_id:
        return SupersetEmbedConfig(
            superset_domain=settings.superset_url,
            dashboard_id=None,
            guest_token=None,
            available=False,
            message="Define SUPERSET_DASHBOARD_ID cuando tengas un dashboard embebible en Superset.",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            login = await client.post(
                f"{settings.superset_internal_url}/api/v1/security/login",
                json={
                    "username": settings.superset_admin_user,
                    "password": settings.superset_admin_password,
                    "provider": "db",
                    "refresh": True,
                },
            )
            login.raise_for_status()
            access_token = login.json()["access_token"]
            guest = await client.post(
                f"{settings.superset_internal_url}/api/v1/security/guest_token/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "resources": [{"type": "dashboard", "id": settings.superset_dashboard_id}],
                    "rls": [],
                    "user": {"username": "portal-bim", "first_name": "Portal", "last_name": "BIM"},
                },
            )
            guest.raise_for_status()
            return SupersetEmbedConfig(
                superset_domain=settings.superset_url,
                dashboard_id=settings.superset_dashboard_id,
                guest_token=guest.json().get("token"),
                available=True,
                message="Superset embed listo.",
            )
    except Exception as exc:
        return SupersetEmbedConfig(
            superset_domain=settings.superset_url,
            dashboard_id=settings.superset_dashboard_id,
            guest_token=None,
            available=False,
            message=f"No se pudo obtener guest token de Superset: {exc}",
        )
