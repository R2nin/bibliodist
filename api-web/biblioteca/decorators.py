from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login


def _redir(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    return None


def staff_required(view_func):
    """Exige is_staff=True. Redireciona para login se anônimo, 403 se autenticado sem permissão."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _redir(request)
        if r:
            return r
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    """Exige is_superuser=True."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        r = _redir(request)
        if r:
            return r
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
