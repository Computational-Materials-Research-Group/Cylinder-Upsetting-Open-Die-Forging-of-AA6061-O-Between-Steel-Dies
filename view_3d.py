"""
view_3d.py - shows the axisymmetric upsetting result as a 3D cylinder in ParaView.

Inside ParaView: View > Python Shell > Run Script > select this file.
(Or from a terminal in the folder:  paraview --script=view_3d.py)

Pipeline:
  upsetting.pvd -> Warp By Vector (U)      deformed shape
                -> Reflect (Y Min)         add the lower half (skipped if frd2vtu.py
                                           was run with --mirror-y or --press)
                -> Extract Surface
                -> Transform (rotate 90 deg about X): the symmetry axis becomes Z
                -> Rotational Extrusion    spin the section around the axis
Coloured by PEEQ (equivalent plastic strain). Press Play to animate.
"""
import os
from paraview.simple import *

SWEEP_ANGLE = 270.0   # 360 = full cylinder, 270 = quarter cut away to see inside
FIELD = "PEEQ"        # or "S_Mises" for von Mises stress
FIELD_RANGE = (0.0, 1.4)

try:
    folder = os.path.dirname(os.path.abspath(__file__))
except NameError:
    folder = os.getcwd()
pvd = os.path.join(folder, "upsetting.pvd")

src = FindSource("upsetting.pvd") or PVDReader(registrationName="upsetting.pvd", FileName=pvd)

warp = WarpByVector(Input=src)
warp.Vectors = ["POINTS", "U"]

# Mirror about the mid-height plane (y = 0), unless frd2vtu.py already wrote
# the full part (--mirror-y or --press), in which case the data has y < 0.
src.UpdatePipeline()
ymin = src.GetDataInformation().GetBounds()[2]
if ymin < -1e-6:
    full = warp
else:
    full = Reflect(Input=warp)
    full.Plane = "Y Min"
    full.CopyInput = 1

surf = ExtractSurface(Input=full)

upright = Transform(Input=surf)     # axis Y -> axis Z
upright.Transform = "Transform"
upright.Transform.Rotate = [90.0, 0.0, 0.0]

solid = RotationalExtrusion(Input=upright)
solid.Resolution = 72
solid.Angle = SWEEP_ANGLE
solid.Capping = 1

view = GetActiveViewOrCreate("RenderView")
for s in (src, warp, full, surf, upright):
    Hide(s, view)
disp = Show(solid, view)
ColorBy(disp, ("POINTS", FIELD))
lut = GetColorTransferFunction(FIELD)
lut.ApplyPreset("Jet", True)
lut.AutomaticRescaleRangeMode = "Never"
lut.RescaleTransferFunction(*FIELD_RANGE)
disp.SetScalarBarVisibility(view, True)

view.InteractionMode = "3D"
view.CameraPosition = [60.0, -70.0, 45.0]
view.CameraFocalPoint = [0.0, 0.0, 0.0]
view.CameraViewUp = [0.0, 0.0, 1.0]
view.ResetCamera()

scene = GetAnimationScene()
scene.UpdateAnimationUsingDataTimeSteps()
scene.GoToLast()
Render(view)
print("3D view ready - press Play to animate the forging.")
