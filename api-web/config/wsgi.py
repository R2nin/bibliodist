"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Remove SCRIPT_NAME do environ para evitar que Gunicorn o repasse ao WSGI
# e Django rejeite requests que não começam com esse prefixo.
os.environ.pop('SCRIPT_NAME', None)

application = get_wsgi_application()

# WhiteNoise em modo WSGI com prefix explícito.
#
# Por que não usar WhiteNoiseMiddleware no MIDDLEWARE do Django:
# O Traefik faz StripPrefix(/bibliodist) antes de enviar ao Gunicorn, então
# PATH_INFO chega como /static/x. O middleware Django compararia /static/x
# com STATIC_URL=/bibliodist/static/ e não encontraria o arquivo.
# No modo WSGI com prefix='static', o WhiteNoise interpreta diretamente
# /static/x e serve o arquivo correto.
from whitenoise import WhiteNoise
from django.conf import settings as _settings

application = WhiteNoise(application, root=str(_settings.STATIC_ROOT), prefix='static')
