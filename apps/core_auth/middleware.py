import threading

_thread_locals = threading.local()

def get_current_tenant_and_user():
    """Retorna (tenant_id, user_email) almacenados en el hilo de ejecución actual."""
    tenant_id = getattr(_thread_locals, 'tenant_id', None)
    user_email = getattr(_thread_locals, 'user_email', None)
    return tenant_id, user_email


class TenantMiddleware:
    """
    Middleware Multi-Tenant:
    - Extrae el tenant (Empresa) del usuario autenticado y lo adjunta a request.tenant.
    - Setea el contexto en thread-local storage para inyección automática en logs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None
        user_email = 'ANON'

        if hasattr(request, 'user') and request.user.is_authenticated:
            user_email = request.user.correo_electronico
            if getattr(request.user, 'id_empresa', None):
                tenant = request.user.id_empresa

        request.tenant = tenant
        _thread_locals.tenant_id = str(tenant.id) if tenant else 'GLOBAL'
        _thread_locals.user_email = user_email

        response = self.get_response(request)

        # Limpiar thread local al finalizar el request
        _thread_locals.tenant_id = None
        _thread_locals.user_email = None

        return response
