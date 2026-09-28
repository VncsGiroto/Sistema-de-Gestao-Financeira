"""Isolamento de Redis para a suite de integração.

Causa-raiz: `app.core.redis_client.get_redis()` memoiza uma conexão global
criada a partir de `settings.redis_url` (lido no import). Os fixtures de
integração fazem `monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)` + `flushdb`
no banco TEST, mas o app continua usando a conexão memoizada do banco padrão
(redis://redis:6379/0). Resultado: contadores de rate-limit/deny-list vazam
entre testes e a suite completa falha com 429/KeyError, enquanto arquivos
isolados passam.

Correção (só teste, sem mudar prod): se TEST_REDIS_URL estiver definido no
ambiente antes da coleta, aponta `settings.redis_url` para ele e descarta a
conexão memoizada, de modo que o app e os fixtures usem o mesmo banco
(que cada fixture limpa com flushdb no setup).
"""

import os

_test_redis = os.getenv("TEST_REDIS_URL")
if _test_redis:
    from app.core import config as _cfg
    from app.core import redis_client as _rc

    _cfg.settings.redis_url = _test_redis
    try:
        _rc._redis = None
    except AttributeError:
        pass
