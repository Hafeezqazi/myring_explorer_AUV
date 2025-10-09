"""
Numerical conversion of the updated truncated Myring profile workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass
class MyringParams:
    """
    Tunable constants mirroring the MATLAB myring_truncated_pure.m script.
    """

    d: float = 0.254  # Maximum diameter [m]
    n_head: float = 2.0  # Myring head exponent
    head_size: float = 0.155  # Full head length 'a' [m]
    mid_size: float = 1.987  # Full mid-cylinder length 'b' [m]
    tail_size: float = 0.7715  # Full tail length 'c' [m]
    theta_deg: float = 11.7  # Tail half-angle at the tip [deg]
    a_offset: float = 0.055  # Nose truncation offset [m]
    c_offset: float = 0.2235  # Tail truncation offset [m]
    r_front_desired: Optional[float] = None  # Target front radius after cut
    r_stern_desired: Optional[float] = None  # Target stern radius after cut
    points_per_meter: int = 1000  # Discretisation density
    rho: float = 1030.0  # Seawater density [kg/m^3]
    nu: float = 1.19e-6  # Kinematic viscosity [m^2/s]
    U: Optional[float] = 2.0  # Speed for ITTC friction estimate [m/s]

    @property
    def theta_rad(self) -> float:
        return np.deg2rad(self.theta_deg)

    @property
    def a_full(self) -> float:
        return self.head_size

    @property
    def b_full(self) -> float:
        return self.mid_size

    @property
    def c_full(self) -> float:
        return self.tail_size


@dataclass
class MyringResults:
    """
    Bundle of calculated profile data.
    """

    params: MyringParams
    offsets: Tuple[float, float]
    lengths: Tuple[float, float, float, float]  # (a_eff, b_full, c_eff, L)
    x_values: np.ndarray
    radii: np.ndarray
    areas: np.ndarray
    front_radius: float
    stern_radius: float
    volume: float
    cb: np.ndarray
    L_over_D: float
    surface_area: float
    Re_L: Optional[float]
    Cf: Optional[float]
    Df: Optional[float]
    surface: Dict[str, np.ndarray]


def _ra_full(s: np.ndarray, d: float, n: float, a: float) -> np.ndarray:
    return (d / 2.0) * np.power(np.maximum(1.0 - np.power(s / a, 2.0), 0.0), 1.0 / n)


def _rc_full(dx: np.ndarray, d: float, theta: float, c: float) -> np.ndarray:
    return (
        (0.5 * d)
        - ((1.5 * d / c**2) - (np.tan(theta) / c)) * np.power(dx, 2.0)
        + ((d / c**3) - (np.tan(theta) / c**2)) * np.power(dx, 3.0)
    )


def _rb_full(x: np.ndarray, d: float) -> np.ndarray:
    return np.full_like(x, 0.5 * d, dtype=float)


def _solve_tail_offset(
    target_radius: float, d: float, theta: float, c_full: float
) -> float:
    """
    Invert Rc_full(c_full - c_offset) = target via a dense lookup/interpolation.
    """

    grid = np.linspace(0.0, c_full - 1e-9, 2000)
    radii = _rc_full(c_full - grid, d, theta, c_full)
    radii = np.clip(radii, a_min=0.0, a_max=None)

    r_sorted_idx = np.argsort(radii)
    r_sorted = radii[r_sorted_idx]
    grid_sorted = grid[r_sorted_idx]

    target = float(np.clip(target_radius, r_sorted[0], r_sorted[-1]))
    c_offset = float(np.interp(target, r_sorted, grid_sorted))
    return float(np.clip(c_offset, 0.0, c_full - 1e-9))


def compute_myring_profile(params: MyringParams) -> MyringResults:
    """
    Compute the truncated Myring profile plus hydrostatic metrics.
    """

    if params.d <= 0:
        raise ValueError("Diameter must be positive.")
    if params.head_size <= 0 or params.tail_size <= 0:
        raise ValueError("Head and tail lengths must be positive.")
    if params.n_head <= 0:
        raise ValueError("Head exponent (n_head) must be positive.")
    if params.points_per_meter < 3:
        raise ValueError("points_per_meter must be at least 3 for stability.")

    d = params.d
    n = params.n_head
    a_full = params.a_full
    b_full = params.b_full
    c_full = params.c_full
    theta = params.theta_rad

    # Adjust offsets if desired radii are specified.
    a_offset = float(params.a_offset)
    if params.r_front_desired is not None:
        y = (2.0 * params.r_front_desired / d) ** n
        y = float(np.clip(y, 0.0, 1.0))
        a_offset = a_full * (1.0 - np.sqrt(1.0 - y))
        a_offset = float(np.clip(a_offset, 0.0, a_full - 1e-9))

    c_offset = float(params.c_offset)
    if params.r_stern_desired is not None:
        c_offset = _solve_tail_offset(params.r_stern_desired, d, theta, c_full)

    a_eff = a_full - a_offset
    c_eff = c_full - c_offset
    L = a_eff + b_full + c_eff

    if a_eff <= 0 or c_eff <= 0:
        raise ValueError(
            "Offsets truncate the head or tail entirely. Adjust offsets or desired radii."
        )

    # Discretisation counts (no duplicate endpoints between segments).
    Na = max(3, int(round(a_eff * params.points_per_meter)))
    Nb = max(3, int(round(b_full * params.points_per_meter)))
    Nc = max(3, int(round(c_eff * params.points_per_meter)))

    x_head = np.linspace(0.0, a_eff, Na + 1, endpoint=True)[:-1]  # drop last
    x_mid = np.linspace(a_eff, a_eff + b_full, Nb + 1, endpoint=True)[:-1]
    x_tail = np.linspace(a_eff + b_full, L, Nc, endpoint=True)

    s_head = x_head - a_eff  # maps to [-a_full + a_offset, 0]
    dx_tail = x_tail - (a_eff + b_full)  # [0, c_eff]

    r_head = _ra_full(s_head, d, n, a_full)
    r_mid = _rb_full(x_mid, d)
    r_tail = _rc_full(dx_tail, d, theta, c_full)

    x = np.concatenate([x_head, x_mid, x_tail])
    r = np.concatenate([r_head, r_mid, r_tail])

    # Ensure monotonic x and non-negative radii.
    x, unique_idx = np.unique(x, return_index=True)
    r = r[unique_idx]
    r = np.clip(r, a_min=0.0, a_max=None)

    if x.size < 3:
        raise ValueError("Insufficient sampling points; increase points_per_meter.")

    front_radius = float(r[0])
    stern_radius = float(r[-1])

    areas = np.pi * np.square(r)
    volume = float(np.trapz(areas, x))
    if volume <= 0.0:
        raise ValueError("Computed volume is non-positive; check parameters.")

    cb_x = float(np.trapz(x * areas, x) / volume)
    cb = np.array([cb_x, 0.0, 0.0], dtype=float)

    L_over_D = L / d

    drdx = np.gradient(r, x, edge_order=2)
    surface_area = float(2.0 * np.pi * np.trapz(r * np.sqrt(1.0 + drdx**2), x))

    Re_L: Optional[float] = None
    Cf: Optional[float] = None
    Df: Optional[float] = None
    if params.U is not None and params.U > 0 and params.nu > 0:
        Re_L = params.U * L / params.nu
        if Re_L <= 0:
            Re_L = None
        else:
            Cf = 0.075 / (np.log10(Re_L) - 2.0) ** 2
            Df = 0.5 * params.rho * params.U**2 * surface_area * Cf

    theta_ring = np.linspace(0.0, 2.0 * np.pi, 120)
    surface_x, surface_theta = np.meshgrid(x, theta_ring)
    surface_r = np.tile(r, (theta_ring.size, 1))
    surface_y = surface_r * np.cos(surface_theta)
    surface_z = surface_r * np.sin(surface_theta)

    surface = {"x": surface_x, "y": surface_y, "z": surface_z}

    return MyringResults(
        params=params,
        offsets=(a_offset, c_offset),
        lengths=(a_eff, b_full, c_eff, L),
        x_values=x,
        radii=r,
        areas=areas,
        front_radius=front_radius,
        stern_radius=stern_radius,
        volume=volume,
        cb=cb,
        L_over_D=L_over_D,
        surface_area=surface_area,
        Re_L=Re_L,
        Cf=Cf,
        Df=Df,
        surface=surface,
    )
