from django.contrib.auth import logout

from .models import AccessLog, SecurityProfile


class SecuritySessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = SecurityProfile.objects.filter(user=request.user).first()
            if profile and profile.is_banned:
                logout(request)
            elif profile:
                session_version = request.session.get('security_session_version')
                if session_version is None:
                    request.session['security_session_version'] = profile.session_version
                elif session_version != profile.session_version:
                    logout(request)

        response = self.get_response(request)
        AccessLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            path=request.path[:255],
            method=request.method,
            ip_address=request.META.get('REMOTE_ADDR'),
            status_code=response.status_code,
        )
        return response