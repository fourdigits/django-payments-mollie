import os

from .settings import *  # noqa: F401, F403

if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.config()}
