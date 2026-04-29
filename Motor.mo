model Motor
  "Techtop TA 56-24 induction motor driving a conveyor belt"

  // ===== Motor parameters =====
  parameter Real Rs_motor = 70.79;
  parameter Real Rr_motor = 18.54;
  parameter Real Lm_motor = 2.276;
  parameter Real Lsigma_motor = 0.1366;
  parameter Real Jr_motor = 7e-5;
  parameter Real Js_motor = 7e-5;
  parameter Integer m_phases = 3;
  parameter Real V_peak = 326.6;
  parameter Real f_grid = 50;

  // ===== Mechanical parameters =====
  parameter Real gear_ratio = 20;
  parameter Real J_gearbox = 5e-5;
  parameter Real drum_radius = 0.025;
  parameter Real load_mass = 1.0;
  parameter Real damper_d = 1;

  // ===== ELECTRICAL =====
  Modelica.Electrical.Polyphase.Sources.SineVoltage sineVoltage(
    final m=m_phases,
    V=fill(V_peak, m_phases),
    phase=-Modelica.Electrical.Polyphase.Functions.symmetricOrientation(m_phases),
    f=fill(f_grid, m_phases),
    offset=zeros(m_phases),
    startTime=zeros(m_phases))
    annotation (Placement(transformation(extent={{-140,10},{-120,30}})));

  Modelica.Electrical.Polyphase.Basic.Star starSupply(final m=m_phases)
    annotation (Placement(transformation(extent={{-140,-30},{-120,-10}})));

  Modelica.Electrical.Polyphase.Basic.Star starMachine(final m=m_phases)
    annotation (Placement(transformation(extent={{-90,-30},{-70,-10}})));

  Modelica.Electrical.Analog.Basic.Ground ground
    annotation (Placement(transformation(extent={{-140,-70},{-120,-50}})));

  Modelica.Electrical.Machines.BasicMachines.InductionMachines.IM_SquirrelCage imc(
    p=2,
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
    frictionParameters(PRef=0, wRef=157, power_w=2),
    statorCoreParameters(PRef=0, VRef=400, wRef=157),
    strayLoadParameters(PRef=0, IRef=1, wRef=157, power_w=1))
    annotation (Placement(transformation(extent={{-90,10},{-70,30}})));

  // ===== MECHANICAL CHAIN =====
  Modelica.Mechanics.Rotational.Sensors.SpeedSensor speedSensor
    annotation (Placement(transformation(extent={{-60,40},{-40,60}})));

  Modelica.Mechanics.Rotational.Components.IdealGear idealGear(
    ratio=gear_ratio)
    annotation (Placement(transformation(extent={{-40,10},{-20,30}})));

  Modelica.Mechanics.Rotational.Components.Inertia inertiaGearBox(
    J=J_gearbox,
    phi(start=0, fixed=true),
    w(start=0, fixed=true))
    annotation (Placement(transformation(extent={{-10,10},{10,30}})));

  Modelica.Mechanics.Rotational.Components.IdealRollingWheel drum(
    radius=drum_radius)
    annotation (Placement(transformation(extent={{20,10},{40,30}})));

  Modelica.Mechanics.Translational.Components.Mass mass(
    m=load_mass,
    s(start=0, fixed=true),
    v(start=0, fixed=true),
    L=0)
    annotation (Placement(transformation(extent={{50,10},{70,30}})));

  Modelica.Mechanics.Translational.Components.Damper damper(d=damper_d)
    annotation (Placement(transformation(extent={{80,10},{100,30}})));

  Modelica.Mechanics.Translational.Components.Fixed fixed
    annotation (Placement(transformation(extent={{110,10},{130,30}})));

equation
  // ===== Electrical connections =====
  connect(sineVoltage.plug_p, imc.plug_sp)
    annotation (Line(points={{-120,20},{-80,20},{-80,30}}, color={0,0,255}));
  connect(sineVoltage.plug_n, starSupply.plug_p)
    annotation (Line(points={{-140,20},{-140,-20}}, color={0,0,255}));
  connect(starSupply.pin_n, ground.p)
    annotation (Line(points={{-120,-20},{-120,-50}}, color={0,0,255}));
  connect(imc.plug_sn, starMachine.plug_p)
    annotation (Line(points={{-86,30},{-86,-20},{-90,-20}}, color={0,0,255}));

  // ===== Mechanical connections =====
  connect(speedSensor.flange, imc.flange)
    annotation (Line(points={{-60,50},{-70,50},{-70,20}}, color={0,0,0}));
  connect(imc.flange, idealGear.flange_a)
    annotation (Line(points={{-70,20},{-40,20}}, color={0,0,0}));
  connect(idealGear.flange_b, inertiaGearBox.flange_a)
    annotation (Line(points={{-20,20},{-10,20}}, color={0,0,0}));
  connect(inertiaGearBox.flange_b, drum.flangeR)
    annotation (Line(points={{10,20},{20,20}}, color={0,0,0}));
  connect(drum.flangeT, mass.flange_a)
    annotation (Line(points={{40,20},{50,20}}, color={0,127,0}));
  connect(mass.flange_b, damper.flange_a)
    annotation (Line(points={{70,20},{80,20}}, color={0,127,0}));
  connect(damper.flange_b, fixed.flange)
    annotation (Line(points={{100,20},{120,20}}, color={0,127,0}));

  annotation(
    experiment(StopTime=3, Interval=0.001, Tolerance=1e-5),
    uses(Modelica(version="4.1.0")),
    Diagram(coordinateSystem(extent={{-160,-80},{140,80}})));

end Motor;
