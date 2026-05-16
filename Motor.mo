model Conveyor_updated "Multiphysics conveyor motor model for ALIX line digital twin.
   Parameterised on TECHTOP TIA56-2 nameplate (0.09 kW, 230/400 V Y, 50 Hz, 4-pole).
   Calibrated to TDMS measurement (244 V RMS phase supply).
   Multiphysics: electrical (IMC) + mechanical (gearbox NMRV 030 i=20, drum, belt, damper, load).
   V2 (13 May 2026): added instantaneous phase A current output i_phase_inst
   per supervisor request to enable AC waveform validation against TDMS."


  // ============================================================
  // PARAMETERS
  // ============================================================

  // ----- Electrical -----
  parameter Modelica.Units.SI.Resistance Rs_motor=12.0 
    "Stator resistance per phase";
  parameter Modelica.Units.SI.Resistance Rr_motor=8.0 
    "Rotor resistance referred to stator";
  parameter Modelica.Units.SI.Inductance Lm_motor=0.45 "Magnetising inductance";
  parameter Modelica.Units.SI.Inductance Lsigma_motor=0.025 
    "Stator and rotor leakage inductance";
  parameter Modelica.Units.SI.Inertia Jr_motor=1.5e-3 "Rotor inertia";
  parameter Modelica.Units.SI.Inertia Js_motor=1.5e-3 
    "Stator-side referred inertia";
  parameter Integer p_pole_pairs=2 "Number of pole pairs (4-pole motor)";
  parameter Integer m_phases=3 "Number of phases";
  parameter Modelica.Units.SI.Voltage V_peak=244.0*sqrt(2) 
    "Peak phase voltage (calibrated to TDMS: 244 V RMS phase)";
  parameter Modelica.Units.SI.Frequency f_grid=50 "Grid frequency";

  // ----- Loss parameters -----
  parameter Modelica.Units.SI.Power P_friction=6 
    "Bearing/windage losses at rated speed";
  parameter Modelica.Units.SI.Power P_core=10 
    "Iron core losses at rated voltage";
  parameter Modelica.Units.SI.Power P_stray=1.5 
    "Stray load losses at rated current";

  // ----- Mechanical -----
  parameter Real gear_ratio=20 "Gearbox reduction ratio (NMRV 030 i=20)";
  parameter Modelica.Units.SI.Inertia J_gearbox=5e-5 
    "Gearbox output-side inertia";
  parameter Modelica.Units.SI.Length drum_radius=0.025 "Drum radius";
  parameter Modelica.Units.SI.Mass load_mass=1.0 
    "Equivalent translational mass of belt + parts";
  parameter Real damper_d(unit="N.s/m") = 1.0 "Belt + bearing viscous damping";
  parameter Modelica.Units.SI.Force load_force_const=5.0 
    "Constant resistive force on belt (light load representing belt friction + small parts)";

  // ============================================================
  // OUTPUTS (promoted for FMU export)
  // ============================================================

  Modelica.Blocks.Interfaces.RealOutput w_motor(unit="rad/s") 
    "Motor mechanical angular speed"
    annotation (Placement(transformation(extent={{160,60},{180,80}})));

  Modelica.Blocks.Interfaces.RealOutput tau_shaft(unit="N.m") 
    "Motor shaft torque"
    annotation (Placement(transformation(extent={{160,30},{180,50}})));

  Modelica.Blocks.Interfaces.RealOutput v_belt(unit="m/s") 
    "Belt linear velocity"
    annotation (Placement(transformation(extent={{160,0},{180,20}})));

  Modelica.Blocks.Interfaces.RealOutput x_belt(unit="m") "Belt linear position"
    annotation (Placement(transformation(extent={{160,-30},{180,-10}})));

  Modelica.Blocks.Interfaces.RealOutput i_phase(unit="A") 
    "Quasi-RMS phase current (steady-state magnitude)"
    annotation (Placement(transformation(extent={{160,-60},{180,-40}})));

  Modelica.Blocks.Interfaces.RealOutput P_elec(unit="W") 
    "Electrical input power"
    annotation (Placement(transformation(extent={{160,-90},{180,-70}})));

  // NEW (v2): instantaneous phase A current output for AC waveform validation
  Modelica.Blocks.Interfaces.RealOutput i_phase_inst(unit="A") 
    "Instantaneous phase A current (50 Hz AC sinusoid)"
    annotation (Placement(transformation(extent={{160,-120},{180,-100}})));

  // ============================================================
  // ELECTRICAL SUBSYSTEM
  // ============================================================

  Modelica.Electrical.Polyphase.Sources.SineVoltage sineVoltage(
    final m=m_phases,
    V=fill(V_peak, m_phases),
    phase=-Modelica.Electrical.Polyphase.Functions.symmetricOrientation(
        m_phases),
    f=fill(f_grid, m_phases),
    offset=zeros(m_phases),
    startTime=zeros(m_phases))
    annotation (Placement(transformation(extent={{-180,10},{-160,30}})));

  Modelica.Electrical.Polyphase.Basic.Star starSupply(final m=m_phases)
    annotation (Placement(transformation(extent={{-180,-30},{-160,-10}})));

  Modelica.Electrical.Polyphase.Basic.Star starMachine(final m=m_phases)
    annotation (Placement(transformation(extent={{-90,-30},{-70,-10}})));

  Modelica.Electrical.Analog.Basic.Ground ground
    annotation (Placement(transformation(extent={{-180,-70},{-160,-50}})));

  Modelica.Electrical.Polyphase.Sensors.CurrentQuasiRMSSensor currentSensor(
      final m=m_phases)
    annotation (Placement(transformation(extent={{-150,10},{-130,30}})));

  Modelica.Electrical.Polyphase.Sensors.PowerSensor powerSensor(final m=
        m_phases)
    annotation (Placement(transformation(extent={{-120,10},{-100,30}})));

  // ============================================================
  // INDUCTION MOTOR
  // ============================================================

  Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage
    imc(
    p=p_pole_pairs,
    fsNominal=f_grid,
    TsOperational=293.15,
    Rs=Rs_motor,
    TsRef=293.15,
    alpha20s=0.00393,
    Lszero=Lsigma_motor,
    Lssigma=Lsigma_motor,
    Jr=Jr_motor,
    useSupport=false,
    Js=Js_motor,
    useThermalPort=false,
    Lm=Lm_motor,
    Lrsigma=Lsigma_motor,
    Rr=Rr_motor,
    TrRef=293.15,
    alpha20r=0.00393,
    TrOperational=293.15,
    frictionParameters(
      PRef=P_friction,
      wRef=157,
      power_w=2),
    statorCoreParameters(
      PRef=P_core,
      VRef=400,
      wRef=157),
    strayLoadParameters(
      PRef=P_stray,
      IRef=1.5,
      wRef=157,
      power_w=2))
    annotation (Placement(transformation(extent={{-90,10},{-70,30}})));

  // ============================================================
  // MECHANICAL SUBSYSTEM
  // ============================================================

  Modelica.Mechanics.Rotational.Sensors.SpeedSensor motorSpeedSensor
    annotation (Placement(transformation(extent={{-60,40},{-40,60}})));

  Modelica.Mechanics.Rotational.Sensors.TorqueSensor motorTorqueSensor
    annotation (Placement(transformation(extent={{-60,10},{-40,30}})));

  Modelica.Mechanics.Rotational.Components.IdealGear idealGear(ratio=gear_ratio)
    annotation (Placement(transformation(extent={{-30,10},{-10,30}})));

  Modelica.Mechanics.Rotational.Components.Inertia inertiaGearBox(
    J=J_gearbox,
    phi(start=0, fixed=true),
    w(start=0, fixed=true))
    annotation (Placement(transformation(extent={{0,10},{20,30}})));

  Modelica.Mechanics.Rotational.Components.IdealRollingWheel drum(radius=
        drum_radius)
    annotation (Placement(transformation(extent={{30,10},{50,30}})));

  Modelica.Mechanics.Translational.Components.Mass mass(
    m=load_mass,
    s(start=0, fixed=true),
    v(start=0, fixed=true),
    L=0) annotation (Placement(transformation(extent={{60,10},{80,30}})));

  Modelica.Mechanics.Translational.Sensors.SpeedSensor beltSpeedSensor
    annotation (Placement(transformation(extent={{60,40},{80,60}})));

  Modelica.Mechanics.Translational.Sensors.PositionSensor beltPositionSensor
    annotation (Placement(transformation(extent={{60,70},{80,90}})));

  Modelica.Mechanics.Translational.Components.Damper damper(d=damper_d)
    annotation (Placement(transformation(extent={{90,10},{110,30}})));

  Modelica.Mechanics.Translational.Sources.ConstantForce conveyorLoad(
      f_constant=-load_force_const)
    annotation (Placement(transformation(extent={{90,-30},{110,-10}})));

  Modelica.Mechanics.Translational.Components.Fixed fixed
    annotation (Placement(transformation(extent={{120,10},{140,30}})));

equation 
  // ============================================================
  // ELECTRICAL CONNECTIONS
  // ============================================================
  connect(sineVoltage.plug_p, currentSensor.plug_p)
    annotation (Line(points={{-180,20},{-150,20}}, color={0,0,255}));
  connect(currentSensor.plug_n, powerSensor.pc)
    annotation (Line(points={{-130,20},{-120,20}}, color={0,0,255}));
  connect(powerSensor.nc, imc.plug_sp) annotation (Line(points={{-100,20},{-74,20},
          {-74,30}}, color={0,0,255}));
  connect(powerSensor.pv, powerSensor.pc) annotation (Line(points={{-110,30},{-110,
          40},{-120,40},{-120,20}}, color={0,0,255}));
  connect(powerSensor.nv, sineVoltage.plug_n) annotation (Line(points={{-110,10},
          {-110,0},{-160,0},{-160,20}}, color={0,0,255}));
  connect(sineVoltage.plug_n, starSupply.plug_p) annotation (Line(points={{-160,
          20},{-160,0},{-180,0},{-180,-20}}, color={0,0,255}));
  connect(starSupply.pin_n, ground.p) annotation (Line(points={{-160,-20},{-160,
          -36},{-160,-50},{-170,-50}}, color={0,0,255}));
  connect(imc.plug_sn, starMachine.plug_p) annotation (Line(points={{-86,30},{-86,
          -20},{-90,-20}}, color={0,0,255}));

  // ============================================================
  // MECHANICAL CONNECTIONS
  // ============================================================
  connect(motorSpeedSensor.flange, imc.flange)
    annotation (Line(points={{-60,50},{-70,50},{-70,20}}, color={0,0,0}));
  connect(imc.flange, motorTorqueSensor.flange_a)
    annotation (Line(points={{-70,20},{-60,20}}, color={0,0,0}));
  connect(motorTorqueSensor.flange_b, idealGear.flange_a)
    annotation (Line(points={{-40,20},{-30,20}}, color={0,0,0}));
  connect(idealGear.flange_b, inertiaGearBox.flange_a)
    annotation (Line(points={{-10,20},{0,20}}, color={0,0,0}));
  connect(inertiaGearBox.flange_b, drum.flangeR)
    annotation (Line(points={{20,20},{30,20}}, color={0,0,0}));
  connect(drum.flangeT, mass.flange_a)
    annotation (Line(points={{50,20},{60,20}}, color={0,127,0}));
  connect(mass.flange_a, beltSpeedSensor.flange)
    annotation (Line(points={{60,20},{60,50}}, color={0,127,0}));
  connect(mass.flange_a, beltPositionSensor.flange)
    annotation (Line(points={{60,20},{60,80}}, color={0,127,0}));
  connect(mass.flange_b, damper.flange_a)
    annotation (Line(points={{80,20},{90,20}}, color={0,127,0}));
  connect(damper.flange_b, fixed.flange)
    annotation (Line(points={{110,20},{130,20}}, color={0,127,0}));
  connect(conveyorLoad.flange, mass.flange_b) annotation (Line(points={{110,-20},
          {120,-20},{120,0},{80,0},{80,20}}, color={0,127,0}));

  // ============================================================
  // OUTPUT PROMOTIONS
  // ============================================================
  connect(motorSpeedSensor.w, w_motor);
  connect(motorTorqueSensor.tau, tau_shaft);
  connect(beltSpeedSensor.v, v_belt);
  connect(beltPositionSensor.s, x_belt);
  connect(currentSensor.I, i_phase);
  connect(powerSensor.power, P_elec);

  // NEW (v2): instantaneous phase A current — direct access from polyphase plug
  i_phase_inst = currentSensor.plug_p.pin[1].i;

  annotation (
    experiment(
      StopTime=5,
      Interval=0.001,
      Tolerance=1e-4),
    uses(Modelica(version="4.1.0")),
    Diagram(coordinateSystem(extent={{-220,-130},{180,110}})));

end Conveyor_updated;
