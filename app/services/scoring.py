# app/services/scoring.py
from math import sqrt

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b: return 0.0
    return len(a & b) / len(a | b)

def _audio_affinity(a: list[float], b: list[float]) -> float:
    d = sqrt(sum((ai - bi)**2 for ai, bi in zip(a,b)))
    return 1 - d / sqrt(len(a))

def score(userA, userB):
    sA = _jaccard(set(userA["artists"]), set(userB["artists"]))
    sG = _jaccard(set(userA["genres"]), set(userB["genres"]))
    sF = _audio_affinity(userA["audio"], userB["audio"])
    return 0.4*sA + 0.2*sG + 0.4*sF
