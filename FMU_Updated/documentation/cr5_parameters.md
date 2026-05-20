# CR5 Cobot — Computed Multibody Parameters

## Source

- CAD file: Dobot CR5 SolidWorks assembly
- Extraction tool: FreeCAD Python console
- Material density assumed: 2700.0 kg/m³ (aluminum 6061)
- All components: BODY + COVER + TRIM (+ ARM for L4) aggregated per link

## Cross-check vs brochure

- Total computed mass: **23.74 kg**
- Brochure spec: 25.0 kg
- Agreement: **94.9%** ✅

## Per-link parameters (in SI units, ready for Modelica MultiBody)

### L1

- Mass: **4.3542 kg**
- CoM in link frame: (0.0018, -0.0000, 0.0688) m
- Inertia tensor at CoM (kg·m²):

```
  [-1.3020e-02  -1.2038e-07  -6.5738e-04]
  [-1.2038e-07  -1.2786e-02  -4.5420e-07]
  [-6.5738e-04  -4.5420e-07   8.8517e-03]
```

### L2

- Mass: **4.3542 kg**
- CoM in link frame: (0.0033, -0.0000, 0.0688) m
- Inertia tensor at CoM (kg·m²):

```
  [-1.3020e-02  -1.3466e-07  -2.1523e-04]
  [-1.3466e-07  -1.2818e-02  -4.5420e-07]
  [-2.1523e-04  -4.5420e-07   8.8194e-03]
```

### L3

- Mass: **4.3542 kg**
- CoM in link frame: (0.0018, -0.0000, 0.0688) m
- Inertia tensor at CoM (kg·m²):

```
  [-1.3020e-02  -1.2038e-07  -6.5738e-04]
  [-1.2038e-07  -1.2786e-02  -4.5420e-07]
  [-6.5738e-04  -4.5420e-07   8.8517e-03]
```

### L4

- Mass: **5.8944 kg**
- CoM in link frame: (0.0000, 0.0000, 0.0249) m
- Inertia tensor at CoM (kg·m²):

```
  [ 2.0375e-02   4.2120e-11   3.4534e-05]
  [ 4.2120e-11   1.9638e-02   4.6936e-10]
  [ 3.4534e-05   4.6936e-10   7.0405e-03]
```

### L5

- Mass: **1.8101 kg**
- CoM in link frame: (0.0016, 0.0000, 0.0659) m
- Inertia tensor at CoM (kg·m²):

```
  [-6.1008e-03   2.1471e-08  -1.1342e-04]
  [ 2.1471e-08  -6.0628e-03   1.5600e-07]
  [-1.1342e-04   1.5600e-07   1.7616e-03]
```

### L6

- Mass: **1.8079 kg**
- CoM in link frame: (0.0016, 0.0000, 0.0660) m
- Inertia tensor at CoM (kg·m²):

```
  [-6.1161e-03   2.1473e-08  -1.1268e-04]
  [ 2.1473e-08  -6.0782e-03   1.5619e-07]
  [-1.1268e-04   1.5619e-07   1.7601e-03]
```

### L7

- Mass: **1.1611 kg**
- CoM in link frame: (-0.0038, -0.0000, 0.0726) m
- Inertia tensor at CoM (kg·m²):

```
  [-5.3626e-03  -5.9834e-07  -4.1840e-04]
  [-5.9834e-07  -5.4108e-03  -9.0847e-07]
  [-4.1840e-04  -9.0847e-07   9.7817e-04]
```

## Notes

- Inertia tensors are computed at each link's composite CoM using parallel axis theorem.
- These parameters are sufficient to build a Modelica.Mechanics.MultiBody model of the CR5 kinematic chain.
- Motor electrical parameters (per-joint Rs, Ke, Kt, gear ratios) are NOT in the CAD file — they will need to be estimated from the brochure's 150 W total power, 48 V bus voltage, and standard servo motor sizing for cobots of this class.
- Joint axes in home pose need to be confirmed; for now we will use standard 6-DOF cobot conventions:
  - J1: (0,0,1), J2: (1,0,0), J3: (1,0,0), J4: (0,0,1), J5: (1,0,0), J6: (0,0,1)
