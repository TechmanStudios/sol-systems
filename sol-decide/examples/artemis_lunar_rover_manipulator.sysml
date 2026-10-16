// ============================================================================
// SOL-Decide Canonical SysML 2.0 Architecture: Artemis Lunar 6-DOF Manipulator
// ============================================================================
// Stalk Channels:
//   Channel 0: grapple_torque_nm   (N-m,   hard bound [55.0, 145.0])
//   Channel 1: cryo_thermal_k      (K,     hard bound [18.0,  85.0])
//   Channel 2: arm_dry_mass_kg     (kg,    hard bound [20.0,  52.0])
// ============================================================================

package Artemis_Lunar_6DOF_Manipulator_SysML {

    part def HybridSupercapHarmonicDriveArm {
        attribute grapple_torque_nm : Real = 124.0;
        attribute cryo_thermal_k : Real = 64.0;
        attribute arm_dry_mass_kg : Real = 44.5;
        attribute cost : Real = 28.5;
        attribute trl : Real = 8;
        attribute mrl : Real = 7;
        attribute doc : String = "6-DOF titanium-beryllium harmonic-drive robotic arm with supercapacitor peak-torque bus.";
    }

    part def DirectDriveCryoBrushlessArm {
        attribute grapple_torque_nm : Real = 88.0;
        attribute cryo_thermal_k : Real = 72.0;
        attribute arm_dry_mass_kg : Real = 34.0;
        attribute cost : Real = 32.0;
        attribute trl : Real = 7;
        attribute mrl : Real = 7;
        attribute doc : String = "Direct-drive frameless cryo-brushless 6-DOF manipulator with low-mass carbon-PEEK links.";
    }

    part def ElectroHydrostaticHeavyArm {
        attribute grapple_torque_nm : Real = 138.0;
        attribute cryo_thermal_k : Real = 42.0;
        attribute arm_dry_mass_kg : Real = 49.5;
        attribute cost : Real = 39.0;
        attribute trl : Real = 6;
        attribute mrl : Real = 6;
        attribute doc : String = "High-force electro-hydrostatic 6-DOF excavator arm with heated fluid manifold.";
    }

    requirement def GrapplePayloadTorqueReq {
        attribute target : Real = 135.0;
        attribute weight : Real = 1.4;
        attribute channel : Real = 0;
        attribute direction : String = "maximize";
        attribute units : String = "N-m";
        attribute doc : String = "Maximize end-effector grapple and core-drill reaction torque.";
    }

    requirement def CryoShadowThermalMarginReq {
        attribute target : Real = 75.0;
        attribute weight : Real = 1.2;
        attribute channel : Real = 1;
        attribute direction : String = "maximize";
        attribute units : String = "K";
        attribute doc : String = "Maximize actuator thermal survival margin in permanently shadowed craters.";
    }

    requirement def ManipulatorDryMassReq {
        attribute target : Real = 24.0;
        attribute weight : Real = 1.1;
        attribute channel : Real = 2;
        attribute direction : String = "minimize";
        attribute units : String = "kg";
        attribute doc : String = "Minimize 6-DOF manipulator dry mass allocation on rover deck.";
    }

    constraint def GrappleTorqueEnvelope {
        attribute lower : Real = 55.0;
        attribute upper : Real = 145.0;
        attribute channel : Real = 0;
        attribute severity : String = "hard";
        attribute units : String = "N-m";
        attribute doc : String = "Hard joint gearbox & structural reaction torque envelope.";
    }

    constraint def CryoThermalSurvivalBound {
        attribute lower : Real = 18.0;
        attribute upper : Real = 85.0;
        attribute channel : Real = 1;
        attribute severity : String = "hard";
        attribute units : String = "K";
        attribute doc : String = "Hard cryogenic survival & motor winding thermal margin bound.";
    }

    constraint def RoverDeckMassAllocationBound {
        attribute lower : Real = 20.0;
        attribute upper : Real = 52.0;
        attribute channel : Real = 2;
        attribute severity : String = "hard";
        attribute units : String = "kg";
        attribute doc : String = "Hard Artemis lunar rover deck mass allocation limit.";
    }

    assumption def RegolithAbrasionFrictionFactor {
        attribute baseline_value : Real = 1.05;
        attribute uncertainty_sigma : Real = 0.06;
        attribute decay_rate : Real = 0.015;
        attribute units : String = "ratio";
        attribute doc : String = "Lunar highlands/crater regolith dust seal torque penalty.";
    }

    assumption def CraterShadowRadiativeSink {
        attribute baseline_value : Real = 42.0;
        attribute uncertainty_sigma : Real = 0.05;
        attribute decay_rate : Real = 0.01;
        attribute units : String = "K";
        attribute doc : String = "Permanently shadowed region (PSR) radiative sink temperature.";
    }
}
