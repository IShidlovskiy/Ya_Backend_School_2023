from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.handlers.couriers import router as couriers_router
from app.handlers.orders import router as orders_router
from app.extra.error_handler import add_exception_handler
from alembic.config import Config
from alembic import command
from alembic.util import CommandError

alembic_cfg = Config("app/alembic.ini")
alembic_cfg.set_main_option("script_location", "app/db/migrations")
try:
    command.upgrade(alembic_cfg, "head")
except CommandError:
    pass


def get_application() -> FastAPI:
    application = FastAPI()
    application.include_router(orders_router)
    application.include_router(couriers_router)
    return application


#  Настройки для лимита в 10 RPS
limiter = Limiter(key_func=get_remote_address, default_limits=["10/second"])
# Стартуем FastAPI
app = get_application()
# Необходимое для корректной работы лимиттера
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
# Кастомная обработка ошибок на эндпоинтах
add_exception_handler(app)


