"""How long a fal request will take, learned from our own requests (fal's queue gives no estimate:
only queue_position while waiting and metrics.inference_time once done).

One penalised linear model per fal model, updated after every finished request (recursive least
squares with a ridge prior). The prior is the model's typical_seconds from the registry, so the
first guesses are sane and a few odd requests cannot swing the line far. When recent errors are
large the model forgets old requests faster and re-fits; when they are small it settles.

Features: [1, pictures asked for, reference images, queue position at the first look]."""
import logging
import time
from dataclasses import dataclass, field

log = logging.getLogger("dreamlib")

N = 4
PENALTY = 4.0  # ridge strength toward the prior; larger trusts the prior longer
SETTLED, ADAPTING = 0.995, 0.95  # forgetting factors: slow when accurate, fast when not
TARGET_ERROR = 0.25  # mean absolute percentage error under which the model is considered settled
ERROR_SMOOTHING = 0.2
MIN_SECONDS = 1.0


def features(pictures: int = 1, references: int = 0, queue_position: int = 0) -> list[float]:
    return [1.0, float(pictures), float(references), float(queue_position)]


@dataclass
class RecursiveRidge:
    prior: list[float]
    weights: list[float] = field(default_factory=list)
    cov: list[list[float]] = field(default_factory=list)
    error: float = 1.0  # smoothed absolute percentage error; starts pessimistic
    seen: int = 0

    def __post_init__(self):
        self.weights = self.weights or list(self.prior)
        self.cov = self.cov or [[(1 / PENALTY if i == j else 0.0) for j in range(N)] for i in range(N)]

    def predict(self, x: list[float]) -> float:
        return max(MIN_SECONDS, sum(w * v for w, v in zip(self.weights, x)))

    @property
    def forgetting(self) -> float:
        return SETTLED if self.error <= TARGET_ERROR else ADAPTING

    def update(self, x: list[float], y: float) -> float:
        """Folds one observation in and returns the error it had before the update."""
        guess = self.predict(x)
        miss = abs(y - guess) / max(y, MIN_SECONDS)
        self.error = (1 - ERROR_SMOOTHING) * self.error + ERROR_SMOOTHING * miss
        lam, P = self.forgetting, self.cov
        Px = [sum(P[i][j] * x[j] for j in range(N)) for i in range(N)]
        gain_den = lam + sum(x[i] * Px[i] for i in range(N))
        k = [v / gain_den for v in Px]
        residual = y - sum(w * v for w, v in zip(self.weights, x))
        self.weights = [w + ki * residual for w, ki in zip(self.weights, k)]
        self.cov = [[(P[i][j] - k[i] * Px[j]) / lam for j in range(N)] for i in range(N)]
        self.seen += 1
        return miss


class Estimator:
    """Per-model curves, plus an optional store that keeps observations across restarts."""

    def __init__(self, store=None):
        self.store = store  # SupabaseTimings, MemoryTimings or None
        self.curves: dict[str, RecursiveRidge] = {}
        self._warmed = False

    def _curve(self, model: str, typical: float) -> RecursiveRidge:
        if model not in self.curves:
            self.curves[model] = RecursiveRidge(prior=[typical, 0.0, 0.0, 0.0])
        return self.curves[model]

    async def _warm(self) -> None:
        """Replays stored observations, oldest first, once per process."""
        if self._warmed or not self.store:
            return
        self._warmed = True
        try:
            rows = await self.store.recent()
        except Exception:
            log.warning("eta: could not load past timings", exc_info=True)
            return
        for r in rows:
            self._curve(r["model"], r.get("typical_seconds") or 10.0).update(r["features"], r["total_seconds"])

    async def estimate(self, model: str, typical: float, x: list[float]) -> float:
        await self._warm()
        return self._curve(model, typical).predict(x)

    async def observe(self, model: str, typical: float, x: list[float], total: float, inference: float | None) -> None:
        await self._warm()
        curve = self._curve(model, typical)
        miss = curve.update(x, total)
        log.info("eta: %s took %.1fs (inference %s), missed by %.0f%%, error %.0f%%", model, total,
                 f"{inference:.1f}s" if inference is not None else "?", miss * 100, curve.error * 100)
        if self.store:
            try:
                await self.store.insert({"model": model, "typical_seconds": typical, "features": x,
                                         "total_seconds": total, "inference_seconds": inference})
            except Exception:
                log.warning("eta: could not store timing", exc_info=True)


class MemoryTimings:
    def __init__(self):
        self.rows: list[dict] = []

    async def insert(self, row: dict) -> None:
        self.rows.append(row)

    async def recent(self, limit: int = 500) -> list[dict]:
        return self.rows[-limit:]


class SupabaseTimings:
    def __init__(self, sb):
        self.sb = sb

    async def insert(self, row: dict) -> None:
        res = await self.sb._do("POST", "/rest/v1/generation_timings", self.sb.key, json_body=row, prefer="return=minimal")
        if res.status_code // 100 != 2:
            raise RuntimeError(f"timings: status {res.status_code}")

    async def recent(self, limit: int = 500) -> list[dict]:
        params = {"select": "model,typical_seconds,features,total_seconds", "order": "created_at.desc", "limit": str(limit)}
        res = await self.sb._do("GET", "/rest/v1/generation_timings", self.sb.key, params=params)
        if res.status_code // 100 != 2:
            raise RuntimeError(f"timings: status {res.status_code}")
        return list(reversed(res.json()))


def clock() -> float:
    return time.monotonic()
