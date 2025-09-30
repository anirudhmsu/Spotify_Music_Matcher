from math import sqrt
from typing import Iterable, List


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def jaccard(a: Iterable[str] | set[str], b: Iterable[str] | set[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _norm_tempo(bpm: float) -> float:
    # Map 60..200 BPM to 0..1
    return _clamp((bpm - 60.0) / 140.0)


def _norm_loudness(db: float) -> float:
    # Map -60..0 dB to 0..1
    return _clamp((db + 60.0) / 60.0)


def normalize_audio(vec: List[float]) -> List[float]:
    # Expect order: tempo, energy, valence, danceability, acousticness, loudness
    if not vec or len(vec) < 6:
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    tempo, energy, valence, dance, acoustic, loud = vec[:6]
    return [
        _norm_tempo(float(tempo)),
        _clamp(float(energy)),
        _clamp(float(valence)),
        _clamp(float(dance)),
        _clamp(float(acoustic)),
        _norm_loudness(float(loud)),
    ]


def audio_affinity(a: List[float], b: List[float]) -> float:
    an = normalize_audio(a)
    bn = normalize_audio(b)
    d = sqrt(sum((ai - bi) ** 2 for ai, bi in zip(an, bn)))
    # Max distance in this 6-D normalized space is sqrt(6)
    aff = 1.0 - d / sqrt(len(an))
    return _clamp(aff)


def score(userA, userB) -> float:
    sA = jaccard(userA["artists"], userB["artists"])  # artist overlap
    sG = jaccard(userA["genres"], userB["genres"])    # genre overlap
    sF = audio_affinity(userA["audio"], userB["audio"])  # audio profile affinity
    return 0.4 * sA + 0.2 * sG + 0.4 * sF
