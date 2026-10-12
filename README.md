# Cylinder Upsetting (Open-Die Forging) of AA6061-O Between Steel Dies Using CalculiX 

<p align="center">
  <img src="https://img.shields.io/badge/CalculiX-2.21-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Open--Die-Forging-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/AA6061--O-Aluminium-silver?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Axisymmetric-CAX8R-purple?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Contact-Coulomb%20Friction-red?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Plasticity-Hollomon%20Hardening-darkgreen?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/ParaView-VTU%20Export-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=for-the-badge"/>
</p>

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.23315152"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.23315152.svg" alt="DOI"/></a>
</p>

<p align="center">
  A <b>fully scripted, open-source forging model</b>: a short
  <b>AA6061-O aluminium cylinder</b> is compressed to <b>half its height</b>
  between two flat <b>elastic steel dies</b> with <b>Coulomb friction</b>
  at the die faces. The model captures large plastic deformation,
  <b>barreling</b>, <b>dead-metal zones</b> and the folding of the free
  surface onto the dies, reports the <b>forging load versus stroke</b>,
  checks it against the classical hand calculation, and exports
  everything to ParaView and CSV.
</p>

<img width="1008" height="526" alt="cover" src="https://github.com/user-attachments/assets/cc88d3d5-69bb-4d64-ae08-ce27e0bd7e2d" />


---

## Concept

Upsetting is the simplest open-die forging operation and the standard
laboratory test for bulk metal forming: a cylinder is squeezed between
two flat dies so that its height decreases and its diameter grows.

If the die faces were perfectly lubricated, the cylinder would stay
cylindrical and deform uniformly. In practice, **friction at the die
faces restrains the material in contact with the dies**, so the
mid-height expands more than the ends and the part **barrels**. Under
the die centres, material barely deforms (the **dead-metal zones**),
while the strain concentrates at the centre of the workpiece and along
diagonal shear bands. As the barrel grows, the original side surface
**folds over onto the die faces**.

This repository is a compact, validated testbed for that process: one
Python script generates the complete CalculiX model, the solver runs in
about a minute, and post-processing scripts extract the load curve and
produce ParaView animations, including a 3D cutaway of the forged part.

| Aspect | Description |
|---|---|
| Process | Cylinder upsetting (open-die forging), 50% height reduction |
| Workpiece | AA6061-O aluminium, D = 20 mm, H = 20 mm |
| Dies | Flat tool steel blocks, elastic |
| Kinematics | Axisymmetric, large deformation (NLGEOM), quasi-static |
| Material model | Isotropic elastic-plastic, Hollomon flow curve (tabulated) |
| Contact | Surface-to-surface, linear penalty, Coulomb friction |
| Symmetry | Cylinder axis (r = 0) and mid-height plane (y = 0) |
| Elements | CAX8R (8-node axisymmetric, reduced integration) |
| Solver | CalculiX `ccx` 2.21, implicit static, automatic incrementation |
| Output | `.frd` / `.dat`, converted to `.vtu` / `.pvd`; CSV load curve |

---

## Process Sequence

```
  Stage A  SETUP       workpiece and upper die meshed as separate bodies,
                       die face initially touching the workpiece top
  Stage B  UPSETTING   die top face displaced downward by 5 mm
                       (half model -> 10 mm total height reduction, 50 %)
                       automatic increments: first 0.5 %, max 2 % of stroke
  Stage C  OUTPUT      fields at every increment (U, S, PEEQ, RF, contact),
                       die reaction force and two monitor nodes printed
```

---

## Geometry

```
      y (axial)
      |
      |  +---------------------------------------+   y = 15 mm  die top (stroke applied)
      |  |        upper die (steel)              |
      |  +---------------------------------------+   y = 10 mm  die face / workpiece top
      |  +-------------------+
      |  |                   |
      |  |  workpiece        |   AA6061-O
      |  |  (quarter section)|
      |  |                   |
      +--+-------------------+------------------------- r (radial)
      0              r = 10 mm                r = 22 mm
      ^  axis of symmetry (r = 0)
      ^  mid-height symmetry plane at y = 0 represents the lower die

  Full part:  cylinder D = 20 mm x H = 20 mm,  dies 44 mm diameter x 5 mm thick
  Modelled:   r = 0..10 mm, y = 0..10 mm (workpiece) + r = 0..22 mm, y = 10..15 mm (die)
```

CalculiX represents axisymmetric elements as a 2-degree wedge, so printed
forces are multiplied by 180 to obtain the force on the full cylinder.

---

## Physics

### Equilibrium (quasi-static, large deformation)

```
  div(sigma) = 0                      in workpiece and die
  updated geometry at every increment (NLGEOM)
```

Inertia is neglected: forging at press speeds is quasi-static.

### Workpiece plasticity

```
  von Mises yield:        sigma_eq = sigma_f(eps_p)
  Hollomon flow curve:    sigma_f  = K (eps0 + eps_p)^n
  isotropic hardening, tabulated in *PLASTIC up to eps_p = 2.0
```

### Contact at the die face

```
  Normal:      p = K_pen * overclosure          (linear penalty, K_pen = 1e5 MPa/mm)
  Tangential:  |tau| <= mu * p                  (Coulomb, mu = 0.15)
               stick slope 5e4 MPa/mm
  Slave:       workpiece top face + outer side face (captures fold-over)
  Master:      die bottom face
```

### Reference solutions

```
  Volume constancy:     r(H) = R0 * sqrt(H0 / H)
  True strain:          eps  = ln(H0 / H)

  Frictionless (exact): F = sigma_f(eps) * pi * r^2
  Slab method (Siebel): F = sigma_f(eps) * pi * r^2 * (1 + 2 mu r / (3 H))
```

The frictionless case is used for validation; the slab method is the
classical hand calculation shown on the load-stroke plot.

### Boundary conditions

| Node set | Region | Constraint |
|---|---|---|
| `AXIS` | All nodes on r = 0 (workpiece and die) | Radial displacement u_r = 0 |
| `SYM` | Workpiece nodes on y = 0 | Axial displacement u_y = 0 |
| `DIETOP` | Top face of the die | u_r = 0, u_y = -5 mm (ramped over the step) |
| Die / workpiece | Die face and workpiece top + side | Contact with friction |

---

## Material Properties

| Property | AA6061-O (workpiece) | Tool steel (die) | Unit |
|---|---|---|---|
| Young's modulus E | 69,000 | 210,000 | MPa |
| Poisson's ratio | 0.33 | 0.30 | n/a |
| Strength coefficient K | 205 | elastic | MPa |
| Hardening exponent n | 0.20 | n/a | n/a |
| Strain offset eps0 | 0.004 | n/a | n/a |
| Initial yield stress | 68 | n/a | MPa |
| Flow stress at eps = 0.69 | 191 | n/a | MPa |

The flow curve is a typical literature fit for annealed 6061 aluminium.
Replace `FLOW_K`, `FLOW_N` and `EPS0` with your own compression-test data
for quantitative work.

---

## Process Parameters

### Geometry and process

| Parameter | Symbol | Default | Unit |
|---|---|---|---|
| Cylinder radius | `RADIUS` | 10 | mm |
| Cylinder height | `HEIGHT` | 20 | mm |
| Height reduction | `REDUCTION` | 0.50 | n/a |
| Friction coefficient | `FRICTION` | 0.15 | n/a |
| Die radius | `DIE_RADIUS` | 22 | mm |
| Die thickness | `DIE_THICK` | 5 | mm |

### Material

| Parameter | Symbol | Default | Unit |
|---|---|---|---|
| Workpiece Young's modulus | `E_WORK` | 69,000 | MPa |
| Workpiece Poisson's ratio | `NU_WORK` | 0.33 | n/a |
| Flow curve coefficient | `FLOW_K` | 205 | MPa |
| Flow curve exponent | `FLOW_N` | 0.20 | n/a |
| Strain offset | `EPS0` | 0.004 | n/a |
| Die Young's modulus | `E_DIE` | 210,000 | MPa |
| Die Poisson's ratio | `NU_DIE` | 0.30 | n/a |

### Numerical

| Parameter | Symbol | Default | Unit |
|---|---|---|---|
| Workpiece elements (radial x axial) | `NR`, `NZ` | 20, 20 | n/a |
| Die elements (radial x axial) | `DIE_NR`, `DIE_NZ` | 30, 4 | n/a |
| Initial / max increment | in `*STATIC` | 0.005 / 0.02 | of step |
| Minimum increment | in `*STATIC` | 1e-5 | of step |
| Contact penalty stiffness | in `*SURFACE BEHAVIOR` | 1e5 | MPa/mm |
| Friction stick slope | in `*FRICTION` | 5e4 | MPa/mm |

All parameters except the last four are set at the top of
`build_upsetting.py`.

---

## Derived Design Values (computed from the default inputs)

These follow directly from the parameters above. They are **not**
simulation results.

| Quantity | Value |
|---|---|
| Initial cross-section | 314.2 mm² |
| Load at first yield | ≈ 21 kN |
| Final height | 10 mm |
| Final true (logarithmic) strain | ln 2 ≈ 0.693 |
| Uniform-volume final radius | 14.14 mm |
| Flow stress at final strain | ≈ 191 MPa |
| Frictionless final load (exact) | ≈ 119.6 kN |
| Slab-method final load (mu = 0.15) | ≈ 136.6 kN |
| Die stroke in the half model | 5 mm |

---

## Mesh

| Quantity | Value |
|---|---|
| Workpiece elements | 400 CAX8R |
| Die elements | 120 CAX8R |
| Total nodes | 1,710 |
| Workpiece element size | 0.5 x 0.5 mm (initial) |
| Die element size | 0.73 x 1.25 mm |

Treat the console line `Mesh: ... elements ... nodes` printed by
`build_upsetting.py` as authoritative; it changes with any mesh
parameter.

---

## Results

Values from the default model (CalculiX 2.21, single core, about 78 s,
53 increments).

### Validation (mu = 0)

| Quantity | CalculiX | Analytical | Difference |
|---|---|---|---|
| Forging load at 50 % reduction | 119.1 kN | 119.6 kN | 0.4 % |
| Final radius | 14.13 mm | 14.14 mm | < 0.1 % |
| Barreling | none | none | n/a |

### Upsetting with friction (mu = 0.15)

| Quantity | Value |
|---|---|
| Maximum forging load | 128.9 kN |
| Slab-method hand calculation | 136.6 kN |
| Bulge radius at mid-height | 14.51 mm |
| Radius at the die face | 12.22 mm |
| Maximum equivalent plastic strain | ≈ 1.4 (folded corners) |

The slab method assumes full sliding over the whole die face and
typically overestimates the load; part of the contact actually sticks.

![Forging load versus stroke](load_stroke.png)

### What to look for

| Field | Expected behaviour |
|---|---|
| `U` | Die moves down 5 mm; workpiece flows outward, more at mid-height |
| `PEEQ` | Low under the die centre (dead-metal zone), highest at the workpiece centre and folded corners, diagonal shear bands between them |
| `S_Mises` | Highest in the deforming centre; die stays elastic |
| `CONTACT` | Contact zone grows as the side surface folds onto the die |
| Load curve | Rises with work hardening and growing contact area; friction lifts it above the frictionless curve |

---

## Output Files

| File | Description |
|---|---|
| `upsetting.inp` | CalculiX input deck written by `build_upsetting.py` |
| `upsetting.frd` | Field results at every increment |
| `upsetting.dat` | Printed die reaction force and monitor-node displacements |
| `upsetting.sta`, `.cvg` | Solver status and convergence history |
| `load_stroke.csv` | Load-stroke curve with hand-calculation comparison |
| `load_stroke.png` | Plot of the load-stroke curve |
| `upsetting_0001.vtu` ... `upsetting_0053.vtu` | ParaView frames from `frd2vtu.py` |
| `upsetting.pvd` | ParaView collection with the correct increment times |

### VTU data fields

| Field | Description |
|---|---|
| `U` | Displacement (mm) |
| `S` | Stress tensor, 6 components (MPa) |
| `S_Mises` | Von Mises stress (MPa) |
| `PEEQ` | Equivalent plastic strain |
| `RF` | Reaction forces (N, per 2-degree wedge) |
| `CONTACT` | Contact quantities (opening, slip, pressure, shear) |
| `ERROR` | CalculiX error estimator |

### CSV columns

```
load_stroke.csv : stroke_mm, height_mm, force_kN, true_strain,
                  bulge_radius_mm, corner_radius_mm, hand_calc_force_kN

stroke_mm          : total height reduction (both dies)
force_kN           : forging load on the full cylinder
bulge_radius_mm    : radius at mid-height (equator monitor node)
corner_radius_mm   : radius of the original top corner (fold-over)
hand_calc_force_kN : slab-method estimate at the same stroke
```

---

## Repository Structure

```
.
├── build_upsetting.py         # Generates the CalculiX input deck (upsetting.inp)
├── postprocess_upsetting.py   # Load-stroke curve, barreling, hand-calculation comparison
├── frd2vtu.py                 # Pure-Python .frd -> .vtu/.pvd converter for ParaView
├── view_3d.py                 # ParaView script: 3D cutaway of the forged cylinder
├── final_peeq.png             # Plastic strain at the end of the stroke
├── load_stroke.png            # Forging load versus stroke
└── README.md                  # This file
```

---

## How to Run

### Requirements
* CalculiX `ccx` 2.21 or later: http://www.calculix.de
* Python 3 (standard library only for model generation and conversion)
* matplotlib (optional, for the load-stroke plot)
* ParaView 5.10 or later: https://www.paraview.org

On Ubuntu or WSL:

```bash
sudo apt install calculix-ccx python3-matplotlib
```

### Step 1: Generate the model

```bash
python3 build_upsetting.py
```

### Step 2: Run the solver

```bash
ccx upsetting
```

The job name is given without the `.inp` extension. The run takes about
1 to 2 minutes on a single core.

### Step 3: Post-process

```bash
python3 postprocess_upsetting.py
python3 frd2vtu.py upsetting.frd
```

The first command prints the maximum load, final height and barreling
and writes `load_stroke.csv` / `load_stroke.png`; the second writes the
ParaView files.

`frd2vtu.py` has two options for half models with a mid-height symmetry
plane:

```bash
python3 frd2vtu.py upsetting.frd --mirror-y    # full part, both dies close symmetrically
python3 frd2vtu.py upsetting.frd --press 5.0   # full part, lower die fixed (press view)
```

With `--press`, the whole part is shifted down by 5 mm x time, so the
lower die stays fixed and the upper die travels the full 10 mm, as in a
real press. This is a rigid-body shift only: strains, stresses and loads
are unchanged. With either option, do not apply a Reflect filter in
ParaView (`view_3d.py` detects this automatically).

---

## Visualisation in ParaView

### Option A: 2D cross-section

```
Open upsetting.pvd, click Apply
Filters > Warp By Vector, Vectors = U, Apply
Colour by PEEQ (or S_Mises)
Click the "3D" button so it reads "2D", set view direction to -Z
Press Play
```

Node coordinates are the undeformed positions; without Warp By Vector
the undeformed shape is shown at every frame.

### Option B: 3D cutaway of the forged cylinder

```
Open upsetting.pvd, click Apply
View > Python Shell > Run Script > view_3d.py
```

The script chains Warp By Vector, Reflect (Y Min), Extract Surface,
Transform (rotate 90 deg about X) and Rotational Extrusion (270 deg).
Set `SWEEP_ANGLE = 360.0` for the full closed cylinder.

### Option C: Full mirrored section

```
Warp By Vector (U) > Reflect, Plane = X Min
Colour by PEEQ
```

### Option D: Press view (lower die fixed)

```
python3 frd2vtu.py upsetting.frd --press 5.0
Open upsetting.pvd > Warp By Vector (U), no Reflect
Colour by PEEQ, press Play
```

---

## Key Numerical Insights

### Separate meshes for die and workpiece
Workpiece and die nodes are generated independently, even where they
coincide at the initial contact face. Shared nodes would weld the two
bodies together and suppress contact and friction.

### Side face in the slave surface
The outer side face of the cylinder is included in the contact slave
surface. During barreling it rolls onto the die face; without it, the
folded material would pass through the die.

### Reduced-integration quadratic elements
CAX8R avoids the volumetric locking that fully integrated elements show
under nearly incompressible plastic flow, and represents the curved
barrel profile well with a modest mesh.

### Axisymmetric force scaling
CalculiX expands axisymmetric elements to a 2-degree wedge internally,
so reaction forces are per 2 degrees and are multiplied by 180 in the
post-processing script.

### Validation before friction
The frictionless run reproduces the exact solution within 0.4 %, which
verifies the geometry, material table, symmetry conditions and force
scaling before friction is introduced.

### Symmetric dies versus press view
The model contains only the upper die; the mid-height symmetry plane
stands in for the lower die. Mirrored, both dies close on the mid-plane
by 5 mm each. A real press usually holds the lower die and moves the
upper die 10 mm. The two differ only by a rigid-body shift of the whole
part, so deformation, stresses and forging load are identical;
`frd2vtu.py --press` produces the press view for animations.

### Contact at the symmetry axis
In axisymmetric contact the contact stiffness is weighted by the radius,
so it vanishes at r = 0. The workpiece node on the axis penetrates the
die by about 0.2 mm at the end of the stroke; elsewhere the penetration
is below 0.02 mm. The effect is confined to the first element at the
axis and does not affect the forging load.

### Monitor nodes
The mid-height equator node and the original top corner node are
printed at every increment, giving the bulge radius and the fold-over
directly from `upsetting.dat` without parsing the field results.

---

## Common Errors and Fixes

| Error / symptom | Cause | Fix |
|---|---|---|
| `ccx: command not found` | CalculiX not installed or not on PATH | `sudo apt install calculix-ccx` (Ubuntu / WSL) |
| `*WARNING reading *STATIC: minimum increment ...` | Minimum increment set very small | Harmless; the default uses 1e-5 |
| Die and workpiece move together, no barreling | Nodes shared at the interface | Keep separate node sets (as in `build_upsetting.py`) |
| Load about 180 times too small | Axisymmetric wedge force not scaled | Multiply by 180 (done in `postprocess_upsetting.py`) |
| `ccx2paraview` fails: no module named `vtk` | ccx2paraview needs the vtk package | Use `frd2vtu.py` instead (no dependencies) |
| `ccx2paraview` TypeError on complex eigenvalues | Incompatible with numpy 2.5 | Use `frd2vtu.py`, or pin `numpy==2.4.4` in its environment |
| `ccx2paraview` segmentation fault | vtk library crash | Use `frd2vtu.py` |
| ParaView shows a flat, undeformed shape | Coordinates are undeformed | Apply Warp By Vector with `U` |
| Two mirrored workpieces side by side | Reflect plane set to X Min instead of Y Min | Use Y Min to mirror about mid-height |
| Both dies move towards the centre | Mid-height symmetry (correct, rigid-body equivalent of a press) | Use `frd2vtu.py --press 5.0` for a fixed lower die |
| Part doubled or overlapping after `--press` / `--mirror-y` | Reflect applied to data that is already mirrored | Do not add Reflect; `view_3d.py` skips it automatically |
| SyntaxError when pasting `view_3d.py` into the Python Shell | Interactive shell cannot take indented blocks pasted line by line | Use **Run Script**, not paste |
| Overlapping duplicate objects in ParaView | Script run several times | Edit > Reset Session, reopen `upsetting.pvd`, run once |
| Colours flicker during playback | Colour range rescaled per frame | Fix the range (e.g. PEEQ 0 to 1.4) |

---

## Extending the Model

| Extension | What to change |
|---|---|
| Frictionless validation | Set `FRICTION = 0.0` |
| Sticking friction | Raise `FRICTION` to 0.5 or more |
| Larger reduction | Increase `REDUCTION` (extend the flow curve table and die radius) |
| Different aspect ratio | Change `HEIGHT` / `RADIUS` (H/D below 2 to avoid buckling) |
| Other alloys | Replace `E_WORK`, `NU_WORK`, `FLOW_K`, `FLOW_N`, `EPS0` |
| Measured flow curve | Replace the Hollomon table in `*PLASTIC` with test data |
| Mesh convergence study | Increase `NR`, `NZ` (load and bulge should converge) |
| Rigid die | Replace the elastic die with `*RIGID BODY` |
| Hot forging | Add temperature-dependent `*PLASTIC` data and a thermal step |
| Ring compression test | Add an inner radius to the workpiece to calibrate friction |
| Parametric study / ML dataset | Loop `build_upsetting.py` over friction, H/D and reduction |

---

## Citation

Mishra, A. (2026). *Cylinder Upsetting (Open-Die Forging) Simulation
using CalculiX* [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.23315152

```bibtex
@software{mishra2026upsetting,
  author       = {Mishra, Akshansh},
  title        = {Cylinder Upsetting (Open-Die Forging) Simulation
                   using CalculiX},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.23315152},
  url          = {https://doi.org/10.5281/zenodo.23315152}
}
```

---

## License

<p>
<a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">
<img alt="Creative Commons Licence" style="border-width:0"
  src="https://i.creativecommons.org/l/by-nc/4.0/88x31.png"/>
</a>
<br/>
This work is licensed under a
<a rel="license" href="http://creativecommons.org/licenses/by-nc/4.0/">
Creative Commons Attribution NonCommercial 4.0 International License</a>.
</p>

You are free to:
* **Share**: copy and redistribute in any medium or format
* **Adapt**: remix, transform, and build upon the material

Under the following terms:
* **Attribution**: give appropriate credit and link to this repository
* **NonCommercial**: not for commercial use without permission

Copyright 2026 Akshansh Mishra.
