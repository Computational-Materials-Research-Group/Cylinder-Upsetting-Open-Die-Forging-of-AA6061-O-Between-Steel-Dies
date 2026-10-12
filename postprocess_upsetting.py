"""
postprocess_upsetting.py - reads the CalculiX results of the upsetting run and
produces the forging load curve.

    python3 postprocess_upsetting.py

Reads upsetting.inp (model data) and upsetting.dat (printed results).
Writes:
    load_stroke.csv    stroke, height, force, true strain, bulge radius
    load_stroke.png    forging load vs stroke, with the classic hand-calculation
                       (slab/Siebel) estimate for comparison (needs matplotlib)

Note: CalculiX models axisymmetric parts as a 2-degree wedge, so printed
forces are multiplied by 180 to get the force on the full cylinder.
The model is the upper half of the cylinder, so the die force is the full
forging force.
"""
import math
import re

# ---------------------------------------------------------------- model data
inp = open("upsetting.inp").read()
m = re.search(r"R = ([\d.]+) mm, H = ([\d.]+) mm, reduction = (\d+)%, friction = ([\d.]+)", inp)
R0, H0, red, MU = float(m[1]), float(m[2]), float(m[3]) / 100, float(m[4])

# flow curve from the *PLASTIC table of the workpiece material
plastic = inp.split("*PLASTIC\n")[1].split("*")[0].strip().splitlines()
curve = [tuple(map(float, line.split(","))) for line in plastic]   # (stress, eps_p)

def flow_stress(eps):
    for (s1, e1), (s2, e2) in zip(curve, curve[1:]):
        if eps <= e2:
            return s1 + (s2 - s1) * (eps - e1) / (e2 - e1)
    return curve[-1][0]

# ---------------------------------------------------------------- dat parsing
blocks = {}            # (kind, set) -> {time: [values]}
lines = open("upsetting.dat").read().splitlines()
i = 0
while i < len(lines):
    hdr = re.match(r"\s*(total force|displacements) \(.*\) for set (\w+) and time\s+(\S+)", lines[i])
    if hdr:
        kind, nset, t = hdr[1], hdr[2], float(hdr[3])
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        vals = [float(v) for v in lines[j].split()]
        blocks.setdefault((kind, nset), {})[t] = vals[-3:]
        i = j
    i += 1

forces = blocks[("total force", "DIETOP")]
eq = blocks.get(("displacements", "EQUATOR"), {})
co = blocks.get(("displacements", "CORNER"), {})

rows = [(0.0, H0, 0.0, 0.0, R0, R0, 0.0)]
for t in sorted(forces):
    stroke = red * H0 * t                    # total height reduction (both dies)
    H = H0 - stroke
    F = -forces[t][1] * 180.0 / 1000.0       # kN, full cylinder
    eps = math.log(H0 / H)
    r_bulge = R0 + eq.get(t, [0, 0, 0])[0]
    r_corner = R0 + co.get(t, [0, 0, 0])[0]
    # hand-calculation (slab method / Siebel): mean pressure = flow stress
    # * (1 + 2*mu*r/(3*h)), radius from volume constancy
    r_vol = R0 * math.sqrt(H0 / H)
    F_hand = flow_stress(eps) * math.pi * r_vol**2 * (1 + 2 * MU * r_vol / (3 * H)) / 1000
    rows.append((stroke, H, F, eps, r_bulge, r_corner, F_hand))

with open("load_stroke.csv", "w") as f:
    f.write("stroke_mm,height_mm,force_kN,true_strain,bulge_radius_mm,"
            "corner_radius_mm,hand_calc_force_kN\n")
    for r in rows:
        f.write(",".join(f"{v:.5f}" for v in r) + "\n")

last = rows[-1]
print(f"Cylinder R0 = {R0} mm, H0 = {H0} mm, friction = {MU}")
print(f"Final height       : {last[1]:.2f} mm  ({last[0] / H0:.0%} reduction)")
print(f"Max forging load   : {max(r[2] for r in rows):.1f} kN "
      f"(hand calculation: {last[6]:.1f} kN)")
print(f"Bulge radius       : {last[4]:.2f} mm at mid-height, "
      f"{last[5]:.2f} mm at the die face "
      f"(uniform-volume radius {R0 * math.sqrt(H0 / last[1]):.2f} mm)")
print("Wrote load_stroke.csv")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = [r[0] for r in rows]
    plt.figure(figsize=(6.5, 4.2))
    plt.plot(s, [r[2] for r in rows], "o-", ms=3, label="CalculiX")
    plt.plot(s, [r[6] for r in rows], "--", label="hand calculation (slab method)")
    plt.xlabel("stroke [mm]")
    plt.ylabel("forging load [kN]")
    plt.title(f"Cylinder upsetting, friction = {MU}")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("load_stroke.png", dpi=150)
    print("Wrote load_stroke.png")
except ImportError:
    print("(install matplotlib for the plot)")
