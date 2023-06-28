from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse


def add_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """
        В JSON схеме задания предполагается отправка кода 400 Bad Request в случае ошибки валидации данных.
        Импорт данной функции в main.py:
        -замещает код 422 (Validation Error) кодом 400 Bad Request с пустым телом сообщения.
        """
        return JSONResponse(status_code=400, content={})
