# Myring Profile Mathematics

This document summarises the mathematical foundations implemented in the **Myring Profile Explorer**.
Formulas use the notation introduced by Prestero and replicated in the original MATLAB script
`myring_truncated_pure.m`. All symbols refer to SI units unless otherwise noted.

---

## 1. Canonical Myring Geometry

A Myring hull is built from three axial segments:

1. **Head (nose)** – smooth polynomial connecting the nose tip to the cylindrical mid-body.
2. **Mid-body** – constant-radius cylindrical region.
3. **Tail (stern)** – smooth polynomial transitioning from the cylinder to the stern opening.

We denote:

- `d` – maximum diameter (i.e., cylinder diameter).
- `a` – full head length (nose tip to head/cylinder junction).
- `b` – cylinder length.
- `c` – full tail length (cylinder to tail tip).
- `n` – Myring head exponent controlling nose bluntness (e.g., `n = 2`).
- `θ` – tail half-angle in radians.

### 1.1 Head radius

Let `s ∈ [-a, 0]` be the axial coordinate measured from the nose tip. The radial profile:

```
Rₐ(s) = (d / 2) · (1 - (s / a)²)^(1 / n)
```

This produces a smooth transition with zero slope at the cylinder junction.

### 1.2 Mid-body radius

For any `x` in the cylindrical section:

```
Rᵦ(x) = d / 2
```

### 1.3 Tail radius

Let `Δx ∈ [0, c]` be measured from the cylinder/tail junction. The tail polynomial:

```
R_c(Δx) = (d / 2)
          - [ (1.5 d / c²) - (tan θ) / c ] · (Δx)²
          + [ (d / c³) - (tan θ) / c² ] · (Δx)³
```

This satisfies continuity in radius and slope with the cylinder and can achieve a desired tail angle.

---

## 2. Truncation (Offsets) and Effective Length

Many designs trim the nose and tail by offsets `a₀` and `c₀` from the full lengths:

```
a_eff = a - a₀
c_eff = c - c₀
L     = a_eff + b + c_eff
```

Where:

- `a₀` – nose truncation measured from the tip toward the head-body junction.
- `c₀` – tail truncation measured from the tail tip toward the tail-body junction.

The solver constructs three axial grids:

```
x_head ∈ [0, a_eff)
x_mid  ∈ [a_eff, a_eff + b)
x_tail ∈ [a_eff + b, L]
```

Radii are evaluated using the original polynomials with the full parameters `a` and `c`. Negative values
are clamped to zero.

---

## 3. Inversion from Target Cut Radii

The tool optionally allows specifying desired radii at the truncation planes:

- `r_front` – radius at the nose cut plane (after trimming `a₀`).
- `r_stern` – radius at the tail cut plane (after trimming `c₀`).

### 3.1 Nose inversion (analytic)

At the nose cut plane the radius expression simplifies to:

```
r_front = (d / 2) · [ 1 - ((-a + a₀) / a)² ]^(1 / n)
```

Let `y = (2 r_front / d)^n`, then:

```
a₀ = a · (1 - sqrt(1 - y))
```

### 3.2 Tail inversion (numeric)

For the stern, set:

```
f(c₀) = R_c(c - c₀) - r_stern
```

The solver finds `c₀` such that `f(c₀) = 0` through dense sampling and linear interpolation (similar
to root-finding). The solution is constrained to `[0, c)`.

---

## 4. Hydrostatic Calculations

Once radius samples `(xᵢ, rᵢ)` are known, basic hydrostatic properties follow from numerical
integration.

### 4.1 Cross-sectional area

```
Aᵢ = π rᵢ²
```

### 4.2 Volume

Using the trapezoidal rule:

```
Volume = ∫ A(x) dx ≈ trapz(xᵢ, Aᵢ)
```

### 4.3 Centre of buoyancy (CB) along x

```
CBₓ = (1 / Volume) · ∫ x A(x) dx ≈ trapz(xᵢ, xᵢ · Aᵢ) / Volume
CB  = [CBₓ, 0, 0]
```

### 4.4 Wetted surface area

Surface area of a body of revolution:

```
S_w = 2π ∫ r(x) √(1 + (dr/dx)²) dx
```

Approximated numerically via `trapz`.

---

## 5. ITTC-57 Friction Drag Estimate

When a forward speed `U` (m/s) is provided:

```
Re_L = U · L / ν
C_f  = 0.075 / ( (log10 Re_L) - 2 )²
D_f  = 0.5 · ρ · U² · S_w · C_f
```

Where:

- `ν` – kinematic viscosity of the fluid,
- `ρ` – fluid density,
- `S_w` – wetted surface area (from §4.4).

---

## 6. Outputs Exposed in the UI

The GUI displays:

- Effective length `L` and L/D ratio,
- Volume, centre of buoyancy `CBₓ`,
- Front and stern radii (in mm),
- Wetted surface area,
- Offsets `a₀`, `c₀` used after inversion,
- Reynolds number, friction coefficient, and friction drag (if speed supplied).

These values are derived directly from the formulas above; the Python core (`calculations.py`) mirrors
the structure described here.

---

## References

1. Prestero, T. **"Verification of a six-degree of freedom simulation model for the REMUS autonomous
   underwater vehicle."** MIT/WHOI Joint Program in Ocean Engineering, 2001.
2. Original MATLAB script `myring_truncated_pure.m` (provided in the project history).
3. ITTC Recommended Procedures, 1957.

Feel free to extend this document with detailed derivations or alternative formulations when adding
new features (e.g., lifting surface estimates, volume curve exports, or optimisation routines).
