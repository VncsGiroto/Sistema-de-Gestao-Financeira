from fastapi import HTTPException, status


def http_error(status_code: int, title: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"type": "about:blank", "title": title, "status": status_code, "detail": detail},
    )


unauthorized = lambda detail="Credenciais inválidas": http_error(status.HTTP_401_UNAUTHORIZED, "Unauthorized", detail)  # noqa: E731
conflict = lambda detail: http_error(status.HTTP_409_CONFLICT, "Conflict", detail)  # noqa: E731
too_many = lambda detail="Muitas tentativas": http_error(status.HTTP_429_TOO_MANY_REQUESTS, "Too Many Requests", detail)  # noqa: E731
unavailable = lambda detail="Serviço temporariamente indisponível": http_error(  # noqa: E731
    status.HTTP_503_SERVICE_UNAVAILABLE, "Service Unavailable", detail
)
