import logging
from .middleware import get_current_tenant_and_user


class TenantContextFilter(logging.Filter):
    """Filtro de contexto multi-tenant que inyecta empresa_id y usuario_email en los registros de log."""
    def filter(self, record):
        tenant_id, user_email = get_current_tenant_and_user()
        record.empresa_id = tenant_id or 'GLOBAL'
        record.usuario_email = user_email or 'ANON'
        return True
