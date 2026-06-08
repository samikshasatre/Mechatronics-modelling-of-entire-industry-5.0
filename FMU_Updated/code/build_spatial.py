"""Generate the ALIX spatial representation diagram as a standalone SVG.

Top-down (X-Y plane) layout. Origin at S1 photoelectric sensor.
+X = belt travel direction. +Y = lateral, away from operator.
Units: millimetres throughout.

Estimated dimensions are dashed; datasheet/brochure dimensions are solid.
Four coupling channels overlaid: vibration, thermal, EMI, part-flow.
"""
import os

# ---- world geometry (mm) -----------------------------------------------------
# All coordinates in physical mm, then scaled to SVG units at the end.

# Conveyor
conveyor_drive_x   = -350
conveyor_tail_x    =  850
conveyor_y         =   0
belt_half_width    =  60
drum_radius        =  25

# Sensors (along centre-line of belt, y=0)
s1 = (   0, 0)   # origin
s2 = ( 250, 0)
s3 = ( 500, 0)

# Conveyor motor + gearbox (below drive drum, on operator side)
motor_x, motor_y, motor_w, motor_h = -425, -200, 150, 100

# XY10 station
xy10_base_x, xy10_base_y = 350, 250
xy10_w, xy10_h           = 300, 200
xy10_x_travel = (250, 450, 250)     # x_min, x_max, y
xy10_y_travel = (350, 150, 350)     # x, y_min, y_max

# Pneumatic station
pneu_x, pneu_y, pneu_w, pneu_h = 700, 250, 150, 100

# CR5 cobot
cr5_base = (500, 600)
cr5_base_r = 150
cr5_reach_r = 1096   # brochure reach

# Control cabinet
cab_x, cab_y, cab_w, cab_h = 200, -500, 400, 200

# Vision system (mounted above XY10 — shown as a small camera icon)
vision = (500, 350)

# Operator side annotation
operator_y = -650

# ---- drawing parameters ------------------------------------------------------
PAD = 200           # mm padding around content
xmin = -800
xmax = 1900
ymin = -800
ymax = 900

# scale to ~1200 px wide SVG
SCALE = 1200 / (xmax - xmin)
W = int((xmax - xmin) * SCALE)
H = int((ymax - ymin) * SCALE)

def tx(x):
    return (x - xmin) * SCALE

def ty(y):
    # SVG y points DOWN, world Y points UP → flip
    return (ymax - y) * SCALE

def s(d):
    return d * SCALE

# ---- SVG assembly ------------------------------------------------------------
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="Georgia, serif" font-size="11">')

# style block
svg.append("""
<defs>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e8e4d8" stroke-width="0.6"/>
  </pattern>
  <pattern id="grid-major" width="200" height="200" patternUnits="userSpaceOnUse">
    <path d="M 200 0 L 0 0 0 200" fill="none" stroke="#d8d0c0" stroke-width="1"/>
  </pattern>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
          orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#444"/>
  </marker>
  <marker id="arrow-flow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
          orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#2d7a3f"/>
  </marker>
  <marker id="arrow-vib" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
          orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#2a5fb8"/>
  </marker>
  <marker id="arrow-emi" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
          orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#c79100"/>
  </marker>
  <radialGradient id="thermal" cx="50%" cy="50%">
    <stop offset="0%"  stop-color="#d94a4a" stop-opacity="0.35"/>
    <stop offset="60%" stop-color="#d94a4a" stop-opacity="0.10"/>
    <stop offset="100%" stop-color="#d94a4a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="thermal-cab" cx="50%" cy="50%">
    <stop offset="0%"  stop-color="#d94a4a" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="#d94a4a" stop-opacity="0"/>
  </radialGradient>
</defs>
<style>
  .label      { fill:#1a1a1a; font-size:11px; }
  .label-bold { fill:#1a1a1a; font-size:12px; font-weight:bold; }
  .label-sml  { fill:#444; font-size:9.5px; }
  .dim        { fill:#666; font-size:9px; font-style:italic; }
  .axis-lbl   { fill:#222; font-size:13px; font-weight:bold; font-family:'Courier New', monospace; }
  .tbc        { fill:#a0521d; font-size:9px; font-style:italic; }
  .title      { fill:#1a1a1a; font-size:18px; font-weight:bold; }
  .subtitle   { fill:#444; font-size:11px; font-style:italic; }
</style>
""")

# background grid
svg.append(f'<rect width="{W}" height="{H}" fill="#fdfcf7"/>')
svg.append(f'<rect width="{W}" height="{H}" fill="url(#grid)"/>')
svg.append(f'<rect width="{W}" height="{H}" fill="url(#grid-major)"/>')

# ---- THERMAL HALOS (drawn early, behind everything) --------------------------
# Conveyor motor thermal halo (T_motor=305 K validated, ΔT=12 K at t=60s)
svg.append(f'<circle cx="{tx(motor_x + motor_w/2)}" cy="{ty(motor_y - motor_h/2)}" '
           f'r="{s(280)}" fill="url(#thermal)"/>')
# Control cabinet thermal halo
svg.append(f'<circle cx="{tx(cab_x + cab_w/2)}" cy="{ty(cab_y - cab_h/2)}" '
           f'r="{s(250)}" fill="url(#thermal-cab)"/>')

# ---- CR5 reach envelope (drawn early, light) ---------------------------------
svg.append(f'<circle cx="{tx(cr5_base[0])}" cy="{ty(cr5_base[1])}" r="{s(cr5_reach_r)}" '
           f'fill="#f0d8c0" fill-opacity="0.18" stroke="#a66828" stroke-width="0.8" '
           f'stroke-dasharray="3,4"/>')
svg.append(f'<text x="{tx(cr5_base[0] + cr5_reach_r*0.65)}" y="{ty(cr5_base[1] + cr5_reach_r*0.65)}" '
           f'class="label-sml" fill="#a66828" font-style="italic">CR5 reach r=1096</text>')

# ---- CONVEYOR ----------------------------------------------------------------
# Belt rectangle (between drum centres, ±half-width)
belt_x_left  = conveyor_drive_x
belt_x_right = conveyor_tail_x
svg.append(f'<rect x="{tx(belt_x_left)}" y="{ty(conveyor_y + belt_half_width)}" '
           f'width="{s(belt_x_right - belt_x_left)}" height="{s(2*belt_half_width)}" '
           f'fill="#3a3a3a" stroke="#1a1a1a" stroke-width="1.2"/>')
# Belt direction stripes (chevrons)
for cx in range(belt_x_left + 100, belt_x_right - 50, 200):
    svg.append(f'<path d="M {tx(cx)} {ty(belt_half_width-10)} '
               f'L {tx(cx+30)} {ty(0)} L {tx(cx)} {ty(-(belt_half_width-10))}" '
               f'fill="none" stroke="#888" stroke-width="1.2" stroke-linecap="round"/>')

# Drums (circles)
svg.append(f'<circle cx="{tx(conveyor_drive_x)}" cy="{ty(0)}" r="{s(drum_radius+20)}" '
           f'fill="#5a4a3a" stroke="#1a1a1a" stroke-width="1.2"/>')
svg.append(f'<circle cx="{tx(conveyor_tail_x)}" cy="{ty(0)}" r="{s(drum_radius+20)}" '
           f'fill="#5a4a3a" stroke="#1a1a1a" stroke-width="1.2"/>')
svg.append(f'<text x="{tx(conveyor_drive_x)}" y="{ty(-120)}" class="label-sml" '
           f'text-anchor="middle">drive drum</text>')
svg.append(f'<text x="{tx(conveyor_tail_x)}" y="{ty(-120)}" class="label-sml" '
           f'text-anchor="middle">tail drum (TBC)</text>')

# Motor + gearbox housing (with thermal annotation)
svg.append(f'<rect x="{tx(motor_x)}" y="{ty(motor_y)}" '
           f'width="{s(motor_w)}" height="{s(motor_h)}" '
           f'fill="#8a7050" stroke="#3a2a1a" stroke-width="1.5" rx="3"/>')
svg.append(f'<text x="{tx(motor_x + motor_w/2)}" y="{ty(motor_y - motor_h/2 + 5)}" '
           f'class="label-bold" text-anchor="middle">MOTOR</text>')
svg.append(f'<text x="{tx(motor_x + motor_w/2)}" y="{ty(motor_y - motor_h/2 - 15)}" '
           f'class="label-sml" text-anchor="middle">TIA56-2 + NMRV30</text>')
svg.append(f'<text x="{tx(motor_x + motor_w/2)}" y="{ty(motor_y - motor_h/2 - 30)}" '
           f'class="label-sml" text-anchor="middle" fill="#a83232">T=305K (Δ12K)</text>')

# ---- SENSORS S1, S2, S3 ------------------------------------------------------
for (sx, sy), name, is_origin in [(s1, "S1", True), (s2, "S2", False), (s3, "S3", False)]:
    # sensor body (small rectangle on operator side, beam crossing belt)
    sensor_off_y = -100  # transmitter side
    target_y     =  100  # receiver side
    # Beam dashed line
    svg.append(f'<line x1="{tx(sx)}" y1="{ty(sensor_off_y)}" x2="{tx(sx)}" y2="{ty(target_y)}" '
               f'stroke="#c00" stroke-width="1.0" stroke-dasharray="2,3" opacity="0.7"/>')
    # transmitter
    svg.append(f'<rect x="{tx(sx)-6}" y="{ty(sensor_off_y)-4}" width="12" height="8" '
               f'fill="#d44" stroke="#600" stroke-width="0.8"/>')
    # receiver
    svg.append(f'<rect x="{tx(sx)-6}" y="{ty(target_y)-4}" width="12" height="8" '
               f'fill="#444" stroke="#000" stroke-width="0.8"/>')
    # label
    color = "#c00" if is_origin else "#1a1a1a"
    weight = "bold" if is_origin else "normal"
    svg.append(f'<text x="{tx(sx)}" y="{ty(sensor_off_y) + 18}" class="label-bold" '
               f'text-anchor="middle" fill="{color}">{name}</text>')

# ORIGIN marker at S1
svg.append(f'<circle cx="{tx(0)}" cy="{ty(0)}" r="5" fill="none" stroke="#c00" '
           f'stroke-width="1.6"/>')
svg.append(f'<circle cx="{tx(0)}" cy="{ty(0)}" r="2" fill="#c00"/>')

# ---- XY10 STATION ------------------------------------------------------------
svg.append(f'<rect x="{tx(xy10_base_x)}" y="{ty(xy10_base_y + xy10_h)}" '
           f'width="{s(xy10_w)}" height="{s(xy10_h)}" '
           f'fill="#e8e4d0" stroke="#5a4a30" stroke-width="1.6" stroke-dasharray="6,3" rx="2"/>')
svg.append(f'<text x="{tx(xy10_base_x + xy10_w/2)}" y="{ty(xy10_base_y + xy10_h + 30)}" '
           f'class="label-bold" text-anchor="middle">XY10</text>')
svg.append(f'<text x="{tx(xy10_base_x + xy10_w/2)}" y="{ty(xy10_base_y + xy10_h + 50)}" '
           f'class="label-sml" text-anchor="middle">3-axis pick &amp; place</text>')

# X-axis travel arrow
svg.append(f'<line x1="{tx(xy10_x_travel[0])}" y1="{ty(xy10_x_travel[2])}" '
           f'x2="{tx(xy10_x_travel[1])}" y2="{ty(xy10_x_travel[2])}" '
           f'stroke="#5a4a30" stroke-width="1.6" marker-end="url(#arrow)" '
           f'marker-start="url(#arrow)"/>')
svg.append(f'<text x="{tx((xy10_x_travel[0]+xy10_x_travel[1])/2)}" y="{ty(xy10_x_travel[2]+25)}" '
           f'class="dim" text-anchor="middle">X stroke 200</text>')

# Y-axis travel arrow
svg.append(f'<line x1="{tx(xy10_y_travel[0])}" y1="{ty(xy10_y_travel[1])}" '
           f'x2="{tx(xy10_y_travel[0])}" y2="{ty(xy10_y_travel[2])}" '
           f'stroke="#5a4a30" stroke-width="1.6" marker-end="url(#arrow)" '
           f'marker-start="url(#arrow)"/>')
svg.append(f'<text x="{tx(xy10_y_travel[0]+25)}" y="{ty((xy10_y_travel[1]+xy10_y_travel[2])/2)}" '
           f'class="dim">Y stroke 200</text>')

# Vision system (camera glyph above XY10)
vx, vy = vision
svg.append(f'<g transform="translate({tx(vx)},{ty(vy)})">'
           f'<rect x="-12" y="-8" width="24" height="16" fill="#444" stroke="#000" rx="2"/>'
           f'<circle cx="0" cy="0" r="5" fill="#aaa" stroke="#000"/>'
           f'<circle cx="0" cy="0" r="2" fill="#222"/>'
           f'</g>')
svg.append(f'<text x="{tx(vx)}" y="{ty(vy)-22}" class="label-sml" text-anchor="middle">SensoPart vision</text>')

# ---- PNEUMATIC STATION -------------------------------------------------------
svg.append(f'<rect x="{tx(pneu_x)}" y="{ty(pneu_y + pneu_h)}" '
           f'width="{s(pneu_w)}" height="{s(pneu_h)}" '
           f'fill="#d8dce8" stroke="#3a4868" stroke-width="1.6" stroke-dasharray="6,3" rx="2"/>')
svg.append(f'<text x="{tx(pneu_x + pneu_w/2)}" y="{ty(pneu_y + pneu_h/2 + 5)}" '
           f'class="label-bold" text-anchor="middle">Pneumatic</text>')
svg.append(f'<text x="{tx(pneu_x + pneu_w/2)}" y="{ty(pneu_y + pneu_h/2 - 8)}" '
           f'class="label-sml" text-anchor="middle">AG10 (4 bar)</text>')

# ---- CR5 COBOT ---------------------------------------------------------------
svg.append(f'<circle cx="{tx(cr5_base[0])}" cy="{ty(cr5_base[1])}" r="{s(cr5_base_r)}" '
           f'fill="#3a4a5c" stroke="#1a2a3c" stroke-width="1.8"/>')
svg.append(f'<circle cx="{tx(cr5_base[0])}" cy="{ty(cr5_base[1])}" r="{s(cr5_base_r-25)}" '
           f'fill="none" stroke="#7a8a9c" stroke-width="1"/>')
svg.append(f'<text x="{tx(cr5_base[0])}" y="{ty(cr5_base[1])+3}" class="label-bold" '
           f'text-anchor="middle" fill="#fff">CR5</text>')
svg.append(f'<text x="{tx(cr5_base[0])}" y="{ty(cr5_base[1])-12}" class="label-sml" '
           f'text-anchor="middle" fill="#dde">6-DOF cobot</text>')

# ---- CONTROL CABINET ---------------------------------------------------------
svg.append(f'<rect x="{tx(cab_x)}" y="{ty(cab_y + cab_h)}" '
           f'width="{s(cab_w)}" height="{s(cab_h)}" '
           f'fill="#bdb29a" stroke="#3a2a1a" stroke-width="1.6" stroke-dasharray="6,3" rx="2"/>')
svg.append(f'<text x="{tx(cab_x + cab_w/2)}" y="{ty(cab_y + cab_h/2 + 12)}" '
           f'class="label-bold" text-anchor="middle">Control cabinet</text>')
svg.append(f'<text x="{tx(cab_x + cab_w/2)}" y="{ty(cab_y + cab_h/2 - 5)}" '
           f'class="label-sml" text-anchor="middle">UC50 / UC53 — S7-1200 PLC</text>')
svg.append(f'<text x="{tx(cab_x + cab_w/2)}" y="{ty(cab_y + cab_h/2 - 22)}" '
           f'class="label-sml" text-anchor="middle">VFD + stepper drivers</text>')

# ---- COUPLING CHANNEL 1: PART FLOW (green, solid) ----------------------------
# Path: S1 → S2 → S3 → XY10 pick → pneumatic → CR5
flow_pts = [
    (0, 0),
    (250, 0),
    (500, 0),
    (500, 200),       # rise off conveyor toward XY10
    (xy10_base_x + xy10_w/2, xy10_base_y + 100),  # at XY10
    (pneu_x + pneu_w/2, pneu_y + pneu_h/2),
    (cr5_base[0] - cr5_base_r - 30, cr5_base[1] - 80),
]
path_d = "M " + " L ".join(f"{tx(x):.1f} {ty(y):.1f}" for x, y in flow_pts)
svg.append(f'<path d="{path_d}" fill="none" stroke="#2d7a3f" stroke-width="2.2" '
           f'stroke-linecap="round" marker-end="url(#arrow-flow)" opacity="0.85"/>')

# ---- COUPLING CHANNEL 2: VIBRATION (blue, wavy) ------------------------------
# Motor → XY10 frame  (path through bench)
svg.append(f'<path d="M {tx(motor_x+motor_w/2):.1f} {ty(motor_y-motor_h):.1f} '
           f'Q {tx(200):.1f} {ty(-50):.1f}, {tx(xy10_base_x+50):.1f} {ty(xy10_base_y+50):.1f}" '
           f'fill="none" stroke="#2a5fb8" stroke-width="1.6" stroke-dasharray="5,3" '
           f'marker-end="url(#arrow-vib)" opacity="0.8"/>')
# CR5 base → bench (small downward arrow)
svg.append(f'<path d="M {tx(cr5_base[0]+30):.1f} {ty(cr5_base[1]-cr5_base_r-5):.1f} '
           f'L {tx(cr5_base[0]+30):.1f} {ty(cr5_base[1]-cr5_base_r-80):.1f}" '
           f'fill="none" stroke="#2a5fb8" stroke-width="1.6" stroke-dasharray="5,3" '
           f'marker-end="url(#arrow-vib)" opacity="0.8"/>')

# ---- COUPLING CHANNEL 3: EMI (gold, dotted) ----------------------------------
# Cabinet → S1 cable, S2 cable, S3 cable (multi-target burst)
for (sx, sy) in [s1, s2, s3]:
    svg.append(f'<path d="M {tx(cab_x+cab_w):.1f} {ty(cab_y+cab_h/2):.1f} '
               f'Q {tx(sx):.1f} {ty(-200):.1f}, {tx(sx):.1f} {ty(sy-30):.1f}" '
               f'fill="none" stroke="#c79100" stroke-width="1.2" stroke-dasharray="2,3" '
               f'marker-end="url(#arrow-emi)" opacity="0.75"/>')
# Cabinet → stepper drives at XY10
svg.append(f'<path d="M {tx(cab_x+cab_w):.1f} {ty(cab_y+cab_h):.1f} '
           f'Q {tx(700):.1f} {ty(-150):.1f}, {tx(xy10_base_x+xy10_w/2):.1f} {ty(xy10_base_y):.1f}" '
           f'fill="none" stroke="#c79100" stroke-width="1.2" stroke-dasharray="2,3" '
           f'marker-end="url(#arrow-emi)" opacity="0.75"/>')

# ---- DIMENSION LINES ---------------------------------------------------------
def hdim(x1, x2, y, label, conf="tbc", offset=40):
    """Horizontal dimension line at y, between x1 and x2."""
    yy = ty(y - offset)
    cls = "tbc" if conf == "tbc" else "dim"
    svg.append(f'<line x1="{tx(x1)}" y1="{yy}" x2="{tx(x2)}" y2="{yy}" '
               f'stroke="#888" stroke-width="0.8" marker-start="url(#arrow)" '
               f'marker-end="url(#arrow)"/>')
    svg.append(f'<line x1="{tx(x1)}" y1="{yy-6}" x2="{tx(x1)}" y2="{yy+6}" stroke="#888" stroke-width="0.8"/>')
    svg.append(f'<line x1="{tx(x2)}" y1="{yy-6}" x2="{tx(x2)}" y2="{yy+6}" stroke="#888" stroke-width="0.8"/>')
    svg.append(f'<text x="{(tx(x1)+tx(x2))/2}" y="{yy-4}" text-anchor="middle" class="{cls}">{label}</text>')

def vdim(y1, y2, x, label, conf="tbc", offset=80):
    """Vertical dimension line at x, between y1 and y2."""
    xx = tx(x + offset)
    cls = "tbc" if conf == "tbc" else "dim"
    svg.append(f'<line x1="{xx}" y1="{ty(y1)}" x2="{xx}" y2="{ty(y2)}" '
               f'stroke="#888" stroke-width="0.8" marker-start="url(#arrow)" '
               f'marker-end="url(#arrow)"/>')
    svg.append(f'<line x1="{xx-6}" y1="{ty(y1)}" x2="{xx+6}" y2="{ty(y1)}" stroke="#888" stroke-width="0.8"/>')
    svg.append(f'<line x1="{xx-6}" y1="{ty(y2)}" x2="{xx+6}" y2="{ty(y2)}" stroke="#888" stroke-width="0.8"/>')
    svg.append(f'<text x="{xx+6}" y="{(ty(y1)+ty(y2))/2 + 3}" class="{cls}">{label}</text>')

# Sensor spacings (horizontal dims along conveyor)
hdim(0, 250,  -belt_half_width - 30, "S1→S2: 250 (TBC)", "tbc", offset=20)
hdim(250, 500, -belt_half_width - 30, "S2→S3: 250 (TBC)", "tbc", offset=20)

# Conveyor total length
hdim(conveyor_drive_x, conveyor_tail_x, -belt_half_width, "Conveyor 1200 (TBC)", "tbc", offset=90)

# Lateral: conveyor → XY10
vdim(0, xy10_base_y + 100, conveyor_tail_x + 50, "250 (TBC)", "tbc", offset=-30)

# CR5 base position (from S1 origin)
svg.append(f'<line x1="{tx(0)}" y1="{ty(0)}" x2="{tx(cr5_base[0])}" y2="{ty(cr5_base[1])}" '
           f'stroke="#a66828" stroke-width="0.6" stroke-dasharray="2,2" opacity="0.5"/>')
svg.append(f'<text x="{tx(120)}" y="{ty(450)}" class="tbc">'
           f'CR5 base at (500, 600) — TBC</text>')

# ---- COORDINATE AXES ---------------------------------------------------------
# X axis arrow at origin
svg.append(f'<line x1="{tx(0)}" y1="{ty(-150)}" x2="{tx(150)}" y2="{ty(-150)}" '
           f'stroke="#c00" stroke-width="2.0" marker-end="url(#arrow)"/>')
svg.append(f'<text x="{tx(160)}" y="{ty(-155)}" class="axis-lbl" fill="#c00">+X</text>')
# Y axis arrow at origin
svg.append(f'<line x1="{tx(-150)}" y1="{ty(0)}" x2="{tx(-150)}" y2="{ty(150)}" '
           f'stroke="#c00" stroke-width="2.0" marker-end="url(#arrow)"/>')
svg.append(f'<text x="{tx(-175)}" y="{ty(160)}" class="axis-lbl" fill="#c00">+Y</text>')
# Origin label
svg.append(f'<text x="{tx(10)}" y="{ty(0)+18}" class="label-bold" fill="#c00">O (S1) = (0,0,0)</text>')

# ---- TITLE AND NORTH/OPERATOR ARROW ------------------------------------------
svg.append(f'<text x="40" y="36" class="title">ALIX Line — Spatial Representation (top-down, X-Y plane)</text>')
svg.append(f'<text x="40" y="56" class="subtitle">'
           f'Origin O at S1 photoelectric sensor · all dimensions in millimetres · '
           f'dashed footprints = TBC at next lab visit</text>')

# Operator side annotation
svg.append(f'<text x="{tx(300)}" y="{ty(operator_y)}" class="label" text-anchor="middle" '
           f'font-style="italic" fill="#666">— operator side —</text>')

# ---- LEGEND (bottom-right) ---------------------------------------------------
lx, ly = W - 360, H - 220
svg.append(f'<rect x="{lx}" y="{ly}" width="340" height="200" '
           f'fill="#fffef8" stroke="#888" stroke-width="0.8" rx="4"/>')
svg.append(f'<text x="{lx+12}" y="{ly+20}" class="label-bold">Coupling channels</text>')

# Part flow
svg.append(f'<line x1="{lx+15}" y1="{ly+38}" x2="{lx+45}" y2="{ly+38}" '
           f'stroke="#2d7a3f" stroke-width="2.2" marker-end="url(#arrow-flow)"/>')
svg.append(f'<text x="{lx+55}" y="{ly+42}" class="label">Part flow (pallet trajectory)</text>')

# Vibration
svg.append(f'<line x1="{lx+15}" y1="{ly+58}" x2="{lx+45}" y2="{ly+58}" '
           f'stroke="#2a5fb8" stroke-width="1.6" stroke-dasharray="5,3" marker-end="url(#arrow-vib)"/>')
svg.append(f'<text x="{lx+55}" y="{ly+62}" class="label">Vibration (motor → frame)</text>')

# EMI
svg.append(f'<line x1="{lx+15}" y1="{ly+78}" x2="{lx+45}" y2="{ly+78}" '
           f'stroke="#c79100" stroke-width="1.2" stroke-dasharray="2,3" marker-end="url(#arrow-emi)"/>')
svg.append(f'<text x="{lx+55}" y="{ly+82}" class="label">EMI (drives → sensor cables)</text>')

# Thermal
svg.append(f'<circle cx="{lx+30}" cy="{ly+100}" r="10" fill="url(#thermal)"/>')
svg.append(f'<text x="{lx+55}" y="{ly+104}" class="label">Thermal halo (motor body, cabinet)</text>')

# Confidence
svg.append(f'<line x1="{lx+15}" y1="{ly+124}" x2="{lx+45}" y2="{ly+124}" '
           f'stroke="#333" stroke-width="1.6"/>')
svg.append(f'<text x="{lx+55}" y="{ly+128}" class="label-sml">solid: from datasheet / nameplate</text>')
svg.append(f'<line x1="{lx+15}" y1="{ly+142}" x2="{lx+45}" y2="{ly+142}" '
           f'stroke="#333" stroke-width="1.6" stroke-dasharray="6,3"/>')
svg.append(f'<text x="{lx+55}" y="{ly+146}" class="label-sml">dashed: estimated, TBC next lab visit</text>')

# Scale bar (200 mm)
svg.append(f'<text x="{lx+12}" y="{ly+172}" class="label-sml" font-weight="bold">Scale</text>')
svg.append(f'<line x1="{lx+60}" y1="{ly+168}" x2="{lx+60+s(200)}" y2="{ly+168}" '
           f'stroke="#000" stroke-width="1.8"/>')
svg.append(f'<line x1="{lx+60}" y1="{ly+163}" x2="{lx+60}" y2="{ly+173}" stroke="#000" stroke-width="1.8"/>')
svg.append(f'<line x1="{lx+60+s(200)}" y1="{ly+163}" x2="{lx+60+s(200)}" y2="{ly+173}" stroke="#000" stroke-width="1.8"/>')
svg.append(f'<text x="{lx+60+s(100)}" y="{ly+186}" class="label-sml" text-anchor="middle">200 mm</text>')

# Caption strip
svg.append(f'<text x="40" y="{H-20}" class="label-sml" font-style="italic">'
           f'Fig.: 2-D top-down spatial layout of the ALIX line. Origin O coincides with the S1 '
           f'photoelectric sensor used as the temporal trigger of the Python state machine; +X '
           f'follows belt travel, +Y is lateral. Four coupling channels are overlaid for use in '
           f'§8 of the project record (coupling-effects matrix).</text>')

svg.append("</svg>")

svg_content = "\n".join(svg)

svg_path = r"C:\Users\satres\Documents\ALIX\FMU_Updated\code\results\diagram.svg"

with open(svg_path, "w", encoding="utf-8") as f:
    f.write(svg_content)

print("OK — SVG written:", os.path.getsize(svg_path), "bytes")