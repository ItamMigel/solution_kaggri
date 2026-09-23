"""Batched MT19937 that reproduces CPython's ``random.Random(int_seed)`` exactly.

``_end_of_day`` builds ``random.Random((seed * 1_000_003) ^ day)`` and then

1. calls ``rng.random()`` once per *empty* tile, player 0's board first,
2. calls ``rng.choice(sorted(remaining_shops))`` on shop-unlock days.

``random()`` consumes two 32-bit words, ``choice`` consumes one word per
``_randbelow`` attempt.  We therefore generate the raw tempered word stream
(``WORDS_PER_DAY`` words is far more than any day can consume: 2*100 tiles *
2 players = 400 words, plus retry headroom) and index into it at runtime.
"""

from __future__ import annotations

import torch

_N = 624
_M = 397
_MATRIX_A = 0x9908B0DF
_UPPER = 0x80000000
_LOWER = 0x7FFFFFFF
_MASK = 0xFFFFFFFF

# Max words a single end-of-day can consume: 400 for the weed rolls + headroom
# for rng.choice retries (each retry is <=50% likely, so 48 spare words is
# ~3e-15 per choice).
WORDS_PER_DAY = 448

_KMAX = 2


def _init_genrand(s: int) -> list[int]:
    mt = [0] * _N
    mt[0] = s & _MASK
    for i in range(1, _N):
        mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & _MASK
    return mt


# init_by_array always starts from init_genrand(19650218); that prefix is
# seed-independent, so precompute it once (and cache it per device -- a fresh
# host->device copy would be illegal inside a CUDA graph capture).
_INIT_CONST = _init_genrand(19650218)
_INIT_CACHE: dict = {}


def _init_const(device) -> torch.Tensor:
    key = str(device)
    t = _INIT_CACHE.get(key)
    if t is None:
        t = torch.tensor(_INIT_CONST, dtype=torch.int64, device=device)
        _INIT_CACHE[key] = t
    return t


def _temper(y: torch.Tensor) -> torch.Tensor:
    y = y ^ (y >> 11)
    y = y ^ ((y << 7) & 0x9D2C5680)
    y = y ^ ((y << 15) & 0xEFC60000)
    y = y ^ (y >> 18)
    return y & _MASK


def _twist(mt: torch.Tensor) -> torch.Tensor:
    """One MT19937 twist of a batch of states ``[Bd, 624]`` (int64, 32-bit values)."""
    y = (mt[:, :-1] & _UPPER) | (mt[:, 1:] & _LOWER)          # kk = 0..622
    f = (y >> 1) ^ ((y & 1) * _MATRIX_A)
    new = torch.empty_like(mt)
    new[:, :_N - _M] = mt[:, _M:] ^ f[:, :_N - _M]            # kk = 0..226
    # kk = 227..622 : new[kk] = new[kk-227] ^ f[kk]; chase the stride-227 chain.
    a = _N - _M                                               # 227
    new[:, a:2 * a] = new[:, :a] ^ f[:, a:2 * a]              # kk = 227..453
    new[:, 2 * a:_N - 1] = new[:, a:a + (_N - 1 - 2 * a)] ^ f[:, 2 * a:_N - 1]
    y_last = (mt[:, _N - 1] & _UPPER) | (new[:, 0] & _LOWER)
    f_last = (y_last >> 1) ^ ((y_last & 1) * _MATRIX_A)
    new[:, _N - 1] = new[:, _M - 1] ^ f_last
    return new


def gen_words(seed_values: torch.Tensor, n_words: int = WORDS_PER_DAY) -> torch.Tensor:
    """``seed_values``: int64 ``[Bd]`` (non-negative).  Returns ``[Bd, n_words]`` int64.

    Bit-exact with ``[random.Random(int(s)).getrandbits(32) for _ in range(n)]``.
    """
    assert n_words <= _N
    device = seed_values.device
    bd = seed_values.shape[0]
    s = seed_values.to(torch.int64)

    mt = _init_const(device).expand(bd, _N).contiguous()

    key = torch.stack([(s >> (32 * w)) & _MASK for w in range(_KMAX)], dim=1)
    key_len = torch.ones(bd, dtype=torch.int64, device=device)
    for w in range(1, _KMAX):
        key_len = key_len + ((s >> (32 * w)) > 0).to(torch.int64)

    zero = torch.zeros(bd, dtype=torch.int64, device=device)
    j = zero.clone()
    i = 1
    for _ in range(max(_N, _KMAX)):
        prev = mt[:, i - 1]
        t = ((prev ^ (prev >> 30)) * 1664525) & _MASK
        kj = torch.gather(key, 1, j.unsqueeze(1)).squeeze(1)
        mt[:, i] = ((mt[:, i] ^ t) + kj + j) & _MASK
        i += 1
        j = j + 1
        j = torch.where(j >= key_len, zero, j)
        if i >= _N:
            mt[:, 0] = mt[:, _N - 1]
            i = 1
    for _ in range(_N - 1):
        prev = mt[:, i - 1]
        t = ((prev ^ (prev >> 30)) * 1566083941) & _MASK
        mt[:, i] = ((mt[:, i] ^ t) - i) & _MASK
        i += 1
        if i >= _N:
            mt[:, 0] = mt[:, _N - 1]
            i = 1
    mt[:, 0] = _UPPER

    mt = _twist(mt)
    return _temper(mt[:, :n_words])


_TWO27 = 67108864.0
_INV253 = 1.0 / 9007199254740992.0


def words_to_doubles(words: torch.Tensor) -> torch.Tensor:
    """Pairs of words -> ``random.random()`` values (float64), matching CPython."""
    a = (words[..., 0::2] >> 5).to(torch.float64)
    b = (words[..., 1::2] >> 6).to(torch.float64)
    return (a * _TWO27 + b) * _INV253


def getrandbits(word: torch.Tensor, k: int) -> torch.Tensor:
    """``random.getrandbits(k)`` for ``1 <= k <= 32`` from one raw word."""
    return word >> (32 - k)
