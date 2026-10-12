"""
frd2vtu.py - converts CalculiX results (.frd) to ParaView files (.vtu + .pvd).
Pure Python: no vtk, numpy or other packages needed.

    python3 frd2vtu.py upsetting.frd                  # model as computed
    python3 frd2vtu.py upsetting.frd --mirror-y       # add the mirrored half (y -> -y)
    python3 frd2vtu.py upsetting.frd --press 5.0      # mirrored + press view

Writes upsetting_0001.vtu, upsetting_0002.vtu, ... (one per saved increment)
and upsetting.pvd, which opens the whole animation in ParaView with the
correct times.

Options for half models with a mid-height symmetry plane at y = 0:
    --mirror-y        Writes the full part by mirroring the model about y = 0.
                      Both dies then close symmetrically on the mid-plane.
    --press STROKE    Mirrors, then shifts everything down by STROKE * time
                      (STROKE = die travel of the half model at time 1, in model
                      units; 5.0 for the default upsetting model). The lower die
                      then stays fixed and the upper die travels 2 * STROKE, as in
                      a real press. Results are unchanged apart from this
                      rigid-body shift, which is added to U.
With either option, do NOT apply a Reflect filter in ParaView.

Fields written (when present in the .frd):
    U (displacement), RF (reaction force), S (stress tensor, 6 components),
    S_Mises (von Mises stress, computed), PEEQ (equivalent plastic strain),
    CONTACT, ERROR, NT (temperature) and any other nodal block, by its name.
"""
import math
import os
import sys

import argparse
ap = argparse.ArgumentParser(description="CalculiX .frd -> ParaView .vtu/.pvd")
ap.add_argument("frd")
ap.add_argument("--mirror-y", action="store_true",
                help="mirror the model about the plane y = 0")
ap.add_argument("--press", type=float, default=None, metavar="STROKE",
                help="mirror and shift down by STROKE*time (lower die fixed)")
args = ap.parse_args()
frd_path = args.frd
base = os.path.splitext(frd_path)[0]
MIRROR = args.mirror_y or args.press is not None
PRESS = args.press

# frd element type -> (VTK cell type, node order from frd to VTK)
ELEM = {
    1: (12, list(range(8))),                         # hex8
    2: (13, list(range(6))),                         # wedge6
    3: (10, list(range(4))),                         # tet4
    4: (25, list(range(12)) + [16, 17, 18, 19, 12, 13, 14, 15]),  # hex20
    5: (26, list(range(9)) + [12, 13, 14, 9, 10, 11]),            # wedge15
    6: (24, list(range(10))),                        # tet10
    7: (5, list(range(3))),                          # tri3
    8: (22, list(range(6))),                         # tri6
    9: (9, list(range(4))),                          # quad4
    10: (23, list(range(8))),                        # quad8
    11: (3, [0, 1]),                                 # beam2
    12: (21, [0, 2, 1]),                             # beam3
}
NICE_NAMES = {"DISP": "U", "FORC": "RF", "STRESS": "S", "PE": "PEEQ",
              "NDTEMP": "NT", "TOSTRAIN": "E", "MESTRAIN": "ME"}


def values_from(line):
    """Fixed-width E12.5 values after the 13-character prefix (' -1' + I10)."""
    s = line[13:].rstrip("\n")
    return [float(s[k:k + 12]) for k in range(0, len(s) - 11, 12)]


nodes = {}          # id -> (x, y, z)
cells = []          # (vtk_type, [node ids])
frames = []         # list of (time, {name: {node: [values]}})

with open(frd_path) as f:
    lines = f.readlines()

i, n = 0, len(lines)
while i < n:
    line = lines[i]
    key = line[:6].strip()

    if key == "2C":                                   # nodes
        i += 1
        while not lines[i].startswith(" -3"):
            l = lines[i]
            nid = int(l[3:13])
            nodes[nid] = tuple(values_from(l)[:3])
            i += 1

    elif key == "3C":                                 # elements
        i += 1
        while not lines[i].startswith(" -3"):
            head = lines[i].split()
            etype = int(head[2])
            conn = []
            i += 1
            while i < n and lines[i].startswith(" -2"):
                conn += [int(x) for x in lines[i].split()[1:]]
                i += 1
            if etype in ELEM:
                vtype, order = ELEM[etype]
                cells.append((vtype, [conn[k] for k in order]))
        # loop ends on ' -3'

    elif key.startswith("100C"):                      # a result block
        t = float(line[12:24])
        i += 1
        name = lines[i].split()[1]                    # ' -4  DISP  4  1'
        i += 1
        while lines[i].startswith(" -5"):
            i += 1
        data = {}
        while not lines[i].startswith(" -3"):
            l = lines[i]
            if l.startswith(" -1"):
                cur = int(l[3:13])
                data[cur] = values_from(l)
            elif l.startswith(" -2"):
                data[cur] += values_from(l)
            i += 1
        if not frames or abs(frames[-1][0] - t) > 1e-15:
            frames.append((t, {}))
        frames[-1][1][NICE_NAMES.get(name, name)] = data
    i += 1

if not nodes or not cells:
    sys.exit("No mesh found in the .frd file.")

# ------------------------------------------------------------- mirroring
# Sign changes under y -> -y for vector and tensor fields.
FLIP = {"U": [1, -1, 1], "RF": [1, -1, 1],
        "S": [1, 1, 1, -1, -1, 1]}          # Sxx Syy Szz Sxy Syz Szx

if MIRROR:
    offset = max(nodes) + 1
    mirror_id = {}
    for nid, (x, y, z) in list(nodes.items()):
        if abs(y) < 1e-9:
            mirror_id[nid] = nid            # node on the symmetry plane: shared
        else:
            mirror_id[nid] = nid + offset
            nodes[nid + offset] = (x, -y, z)
    for vtype, conn in list(cells):
        mc = [mirror_id[c] for c in conn]
        # mirroring flips orientation: reverse the corner order for planar cells
        if vtype in (9, 5):                 # quad4, tri3
            mc = mc[::-1]
        elif vtype == 23:                   # quad8: corners 0-3, mid-sides 4-7
            mc = [mc[0], mc[3], mc[2], mc[1], mc[7], mc[6], mc[5], mc[4]]
        elif vtype == 22:                   # tri6
            mc = [mc[0], mc[2], mc[1], mc[5], mc[4], mc[3]]
        cells.append((vtype, mc))
    for t, fields in frames:
        for name, data in fields.items():
            sign = FLIP.get(name)
            for nid, v in list(data.items()):
                m = mirror_id[nid]
                if m == nid:
                    continue
                if sign:
                    data[m] = [a * b for a, b in zip(v, sign + [1] * len(v))]
                else:
                    data[m] = list(v)

if PRESS is not None:
    for t, fields in frames:
        if "U" in fields:
            for nid in nodes:
                v = fields["U"].setdefault(nid, [0.0, 0.0, 0.0])
                v[1] -= PRESS * t

ids = sorted(nodes)
index = {nid: k for k, nid in enumerate(ids)}


def vtu(path, fields):
    with open(path, "w") as f:
        f.write('<?xml version="1.0"?>\n<VTKFile type="UnstructuredGrid" version="0.1" '
                'byte_order="LittleEndian">\n<UnstructuredGrid>\n')
        f.write(f'<Piece NumberOfPoints="{len(ids)}" NumberOfCells="{len(cells)}">\n')
        f.write('<Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">\n')
        for nid in ids:
            f.write("%.9g %.9g %.9g\n" % nodes[nid])
        f.write("</DataArray></Points>\n<Cells>\n")
        f.write('<DataArray type="Int64" Name="connectivity" format="ascii">\n')
        for _, c in cells:
            f.write(" ".join(str(index[x]) for x in c) + "\n")
        f.write('</DataArray>\n<DataArray type="Int64" Name="offsets" format="ascii">\n')
        off = 0
        for _, c in cells:
            off += len(c)
            f.write(f"{off}\n")
        f.write('</DataArray>\n<DataArray type="UInt8" Name="types" format="ascii">\n')
        f.write("\n".join(str(t) for t, _ in cells) + "\n</DataArray>\n</Cells>\n")
        f.write("<PointData>\n")
        for name, data in fields.items():
            ncomp = max(len(v) for v in data.values()) if data else 1
            f.write(f'<DataArray type="Float64" Name="{name}" '
                    f'NumberOfComponents="{ncomp}" format="ascii">\n')
            zero = [0.0] * ncomp
            for nid in ids:
                v = (data.get(nid, zero) + zero)[:ncomp]
                f.write(" ".join("%.7g" % x for x in v) + "\n")
            f.write("</DataArray>\n")
        f.write("</PointData>\n</Piece>\n</UnstructuredGrid>\n</VTKFile>\n")


written = []
for k, (t, fields) in enumerate(frames, start=1):
    if "S" in fields:                                 # add von Mises stress
        vm = {}
        for nid, s in fields["S"].items():
            sxx, syy, szz, sxy, syz, szx = (s + [0.0] * 6)[:6]
            vm[nid] = [math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                                 + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2))]
        fields["S_Mises"] = vm
    out = f"{base}_{k:04d}.vtu"
    vtu(out, fields)
    written.append((t, os.path.basename(out)))

with open(base + ".pvd", "w") as f:
    f.write('<?xml version="1.0"?>\n<VTKFile type="Collection" version="0.1">\n<Collection>\n')
    for t, name in written:
        f.write(f'<DataSet timestep="{t:.9g}" file="{name}"/>\n')
    f.write("</Collection>\n</VTKFile>\n")

print(f"{len(ids)} nodes, {len(cells)} cells, {len(written)} frames "
      f"(t = {written[0][0]:g} ... {written[-1][0]:g})")
print(f"Fields: {', '.join(frames[-1][1].keys())}")
if PRESS is not None:
    print(f"Press view: mirrored about y = 0, everything shifted down by "
          f"{PRESS} x time (lower die fixed). Do not apply Reflect in ParaView.")
elif MIRROR:
    print("Mirrored about y = 0. Do not apply Reflect in ParaView.")
print(f"Open {os.path.basename(base)}.pvd in ParaView.")
