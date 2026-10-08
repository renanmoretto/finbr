"""Cache em disco para downloads repetidos (COTAHIST, séries SGS).

Diretório: $FINBR_CACHE_DIR, senão $XDG_CACHE_HOME/finbr, senão ~/.cache/finbr.
Desligar: FINBR_NO_CACHE=1.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

HORA = 3600


def diretorio() -> Path:
    if os.environ.get('FINBR_CACHE_DIR'):
        return Path(os.environ['FINBR_CACHE_DIR'])
    base = os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache'
    return Path(base) / 'finbr'


def ativo() -> bool:
    return os.environ.get('FINBR_NO_CACHE', '').lower() not in {'1', 'true', 'yes'}


def obter(chave: str, ttl: float | None, buscar: Callable[[], bytes]) -> bytes:
    """Retorna os bytes em cache para `chave`, ou chama `buscar` e guarda o resultado.

    `ttl` em segundos; None nunca expira. Se `buscar` levantar, nada é gravado.
    """
    if not ativo():
        logger.debug('cache desligado: %s', chave)
        return buscar()

    path = diretorio() / chave
    if path.is_file():
        idade = time.time() - path.stat().st_mtime
        if ttl is None or idade < ttl:
            logger.debug('cache hit: %s (idade %.0fs)', chave, idade)
            return path.read_bytes()
        logger.debug('cache expirado: %s (idade %.0fs, ttl %.0fs)', chave, idade, ttl)
    else:
        logger.debug('cache miss: %s', chave)

    dados = buscar()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # escreve em arquivo temporário para um processo concorrente nunca ler pela metade
        tmp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
        tmp.write_bytes(dados)
        os.replace(tmp, path)
        logger.debug('cache gravado: %s (%d bytes)', chave, len(dados))
    except OSError as e:
        logger.warning('não foi possível gravar o cache em %s: %s', path, e)
    return dados


def _arquivos() -> list[Path]:
    base = diretorio()
    if not base.is_dir():
        return []
    return [p for p in base.rglob('*') if p.is_file()]


def info() -> dict:
    arquivos = _arquivos()
    return {
        'diretorio': str(diretorio()),
        'ativo': ativo(),
        'arquivos': len(arquivos),
        'tamanho_mb': round(sum(p.stat().st_size for p in arquivos) / 1e6, 2),
    }


def limpar() -> int:
    arquivos = _arquivos()
    for p in arquivos:
        p.unlink()
    logger.debug('cache limpo: %d arquivos removidos de %s', len(arquivos), diretorio())
    return len(arquivos)
