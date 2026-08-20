"""
One-Euro Filter — Adaptive Low-Pass Filter for Cursor Smoothing.

Science: The 1€ Filter (Casiez et al., 2012) adapts its cutoff frequency
based on instantaneous signal velocity:
  - Slow hand movement → heavy smoothing → zero jitter
  - Fast hand movement → minimal filtering → zero lag

Reference: https://gery.casiez.net/1euro/
"""
import math
import time


class _LowPassFilter:
    """Single-pole IIR low-pass filter."""
    def __init__(self):
        self._alpha = 1.0
        self._s: float | None = None

    def filter(self, x: float, alpha: float) -> float:
        self._alpha = max(0.0, min(1.0, alpha))
        if self._s is None:
            self._s = x
        else:
            self._s = self._alpha * x + (1.0 - self._alpha) * self._s
        return self._s

    @property
    def last(self) -> float | None:
        return self._s


class OneEuroFilter:
    """
    Adaptive cursor smoothing filter.

    Parameters
    ----------
    min_cutoff : float
        Minimum cutoff frequency (Hz). Lower → smoother at rest.
    beta : float
        Speed coefficient. Higher → less lag during fast moves.
    d_cutoff : float
        Cutoff for the derivative (velocity) signal.
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self._min_cutoff = float(min_cutoff)
        self._beta = float(beta)
        self._d_cutoff = float(d_cutoff)
        self._x_filt = _LowPassFilter()
        self._dx_filt = _LowPassFilter()
        self._last_t: float | None = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        """Compute smoothing factor for given cutoff frequency and timestep."""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: float | None = None) -> float:
        if timestamp is None:
            timestamp = time.perf_counter()

        if self._last_t is None:
            self._last_t = timestamp
            return x

        dt = max(timestamp - self._last_t, 1e-6)
        self._last_t = timestamp

        prev = self._x_filt.last
        dx = 0.0 if prev is None else (x - prev) / dt
        edx = self._dx_filt.filter(dx, self._alpha(self._d_cutoff, dt))

        cutoff = self._min_cutoff + self._beta * abs(edx)
        return self._x_filt.filter(x, self._alpha(cutoff, dt))

    def reset(self):
        self._x_filt = _LowPassFilter()
        self._dx_filt = _LowPassFilter()
        self._last_t = None


class SmoothPoint:
    """
    Convenience wrapper: a 2D point with independent X and Y One-Euro filters.
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007):
        self._fx = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self._fy = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)

    def filter(self, x: float, y: float) -> tuple[float, float]:
        t = time.perf_counter()
        return self._fx.filter(x, t), self._fy.filter(y, t)

    def reset(self):
        self._fx.reset()
        self._fy.reset()

    def update_params(self, min_cutoff: float, beta: float):
        for f in (self._fx, self._fy):
            f._min_cutoff = min_cutoff
            f._beta = beta
