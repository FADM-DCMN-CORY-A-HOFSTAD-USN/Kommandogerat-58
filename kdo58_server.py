"""
Rheinmetall 5.5 cm Gerat 58 Interactive Museum Engine & Univac Aegis Bridge.
Architecture: Asynchronous Combat Loop with Telemetry Uplink
"""

import time
import math
import asyncio
import logging
from typing import Dict, Any, Tuple
from kdo58_univac_aviation_bridge import TriSystemBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s | [KDO58 SERVER] | %(message)s")

def calculate_ballistic_force(mass_kg: float, velocity_m_s: float, barrel_len_m: float = 4.2) -> Dict[str, float]:
    """Computes muzzle energy and internal acceleration force profiles."""
    if barrel_len_m <= 0:
        return {"energy_mj": 0.0, "force_kn": 0.0, "force_tons": 0.0}
        
    kinetic_energy_joules = 0.5 * mass_kg * (velocity_m_s ** 2)
    average_force_newtons = kinetic_energy_joules / barrel_len_m
    
    return {
        "energy_mj": kinetic_energy_joules / 1_000_000,
        "force_kn": average_force_newtons / 1000,
        "force_tons": average_force_newtons / 9806.65
    }

class MechanicalBallisticCam:
    """Simulates the physical 3D Ballistic Cams (Kurvenkorper) found inside the analog computer."""
    def __init__(self):
        self.muzzle_velocity_m_s = 1050.0
        self.projectile_mass_kg = 2.03

    def read_cam_geometry(self, slant_range_meters: float, target_elevation_deg: float) -> Tuple[float, float]:
        if slant_range_meters <= 0:
            return 0.0, 0.0
            
        el_rad = math.radians(target_elevation_deg)
        time_of_flight_sec = slant_range_meters / (self.muzzle_velocity_m_s * math.cos(el_rad) * 0.92)
        gravity_drop_meters = 0.5 * 9.81 * (time_of_flight_sec ** 2)
        elevation_correction_deg = math.degrees(math.atan2(gravity_drop_meters, max(1.0, slant_range_meters)))
        fuze_delay_seconds = time_of_flight_sec + 0.15
        return elevation_correction_deg, fuze_delay_seconds

class Gerat58OilFeedingSystem:
    """Simulates the Rheinmetall mechanical pulse oiler."""
    def __init__(self):
        self.max_capacity_liters = 4.5
        self.current_oil_level_liters = 4.5
        self.injection_nozzles_clear = True
        self.consumption_per_shot = 0.0015 

    def process_recoil_pulse(self, barrel_temp_celsius: float) -> dict:
        pulse_telemetry = {
            "oil_pumped": False,
            "lubrication_status": "CRITICAL_DRY",
            "oil_level_remaining_pct": 0.0
        }

        if not self.injection_nozzles_clear:
            pulse_telemetry["lubrication_status"] = "NOZZLE_CLOGGED"
            return pulse_telemetry

        if self.current_oil_level_liters <= 0.0:
            pulse_telemetry["lubrication_status"] = "RESERVOIR_EMPTY"
            return pulse_telemetry

        actual_consumption = self.consumption_per_shot * (1.5 if barrel_temp_celsius > 150.0 else 1.0)
        self.current_oil_level_liters = max(0.0, self.current_oil_level_liters - actual_consumption)
        
        pulse_telemetry["oil_pumped"] = True
        pulse_telemetry["oil_level_remaining_pct"] = (self.current_oil_level_liters / self.max_capacity_liters) * 100.0
        
        if pulse_telemetry["oil_level_remaining_pct"] <= 15.0:
            pulse_telemetry["lubrication_status"] = "LOW_PRESSURE_WARNING"
            return pulse_telemetry

        pulse_telemetry["lubrication_status"] = "NOMINAL_FILM"
        return pulse_telemetry

class Gerat58StateEngine:
    """State machine managing the 17 interactive features, maintenance, and kinematics."""
    def __init__(self):
        self.current_mode = "TRANSPORT"
        self.pneumatic_pressure_bar = 0.0
        self.system_voltage = 0.0
        self.barrel_temperature_celsius = 20.0
        
        self.hardware_sensors = {
            "breech_block": "DOWN_OPEN",
            "compressed_air_charged": False,
            "extractor_claws_tripped": False
        }
        
        self.oiler = Gerat58OilFeedingSystem()
        
        self.controls: Dict[str, Any] = {
            "1_trigger_pedal": False,
            "2_safety_selector": "SICHER",
            "3_pneumatic_charging_lever": False,
            "13_travel_lock_clamp": True,
            "14_outrigger_jacks": "RETRACTED",
            "7_main_power_switch": False,
            "8_servo_engagement_clutch": False,
            "10_fuze_setter_inductor": 0.0
        }

    def setup_combat_mode(self) -> str:
        if self.controls["13_travel_lock_clamp"]:
            return "CANNOT ENTER COMBAT MODE: Travel Lock Clamp is still engaged!"
        if self.controls["14_outrigger_jacks"] != "DEPLOYED":
            return "CANNOT ENTER COMBAT MODE: Outrigger Support Jacks are unextended!"
            
        self.system_voltage = 110.0
        self.controls["7_main_power_switch"] = True
        self.current_mode = "COMBAT"
        return "System Architecture Switched To: [COMBAT MODE]"

    def setup_maintenance_mode(self) -> str:
        self.system_voltage = 0.0
        self.controls["8_servo_engagement_clutch"] = False
        self.controls["1_trigger_pedal"] = False
        self.current_mode = "MAINTENANCE"
        return "System Architecture Switched To: [MAINTENANCE MODE]"

    def actuate_control(self, feature_name: str, value: Any) -> str:
        if feature_name not in self.controls:
            return "Feature not recognized."
        
        if feature_name == "3_pneumatic_charging_lever" and value is True:
            self.pneumatic_pressure_bar = max(0.0, self.pneumatic_pressure_bar - 5.0)
            self.hardware_sensors["compressed_air_charged"] = True
            return "Feature 3 Actuated: High-pressure air accumulator flask primed."
            
        self.controls[feature_name] = value
        return f"Control Modified: {feature_name} set to {value}"

    def execute_loading_cycle(self) -> Tuple[bool, str]:
        if self.hardware_sensors["breech_block"] != "DOWN_OPEN":
            return False, "RAMMING BLOCKED: Breech wedge must be fully down and open."
        if not self.hardware_sensors["compressed_air_charged"]:
            return False, "PNEUMATIC FAILURE: Accumulator flask pressure too low."
            
        self.hardware_sensors["extractor_claws_tripped"] = True
        self.hardware_sensors["breech_block"] = "UP_CLOSED"
        return True, "Breech loaded, wedge locked home, firing pin cocked."

    def process_firing_sequence(self, cam: MechanicalBallisticCam, range_m: float, elevation_deg: float) -> Dict[str, Any]:
        if self.current_mode != "COMBAT":
            return {"firing_status": "ABORTED", "reason": "Weapon is not in COMBAT mode."}
        if self.controls["2_safety_selector"] == "SICHER":
            return {"firing_status": "ABORTED", "reason": "Safety selector lever is set to SICHER."}

        load_success, load_msg = self.execute_loading_cycle()
        if not load_success:
            return {"firing_status": "ABORTED", "reason": load_msg}

        lead_correction, fuze_time = cam.read_cam_geometry(range_m, elevation_deg)
        self.controls["10_fuze_setter_inductor"] = fuze_time
        force_profile = calculate_ballistic_force(mass_kg=cam.projectile_mass_kg, velocity_m_s=cam.muzzle_velocity_m_s)
        
        self.hardware_sensors["breech_block"] = "DOWN_OPEN"
        self.hardware_sensors["extractor_claws_tripped"] = False
        self.barrel_temperature_celsius += 14.5
        
        oil_status = self.oiler.process_recoil_pulse(self.barrel_temperature_celsius)
        if oil_status['lubrication_status'] in ['RESERVOIR_EMPTY', 'NOZZLE_CLOGGED']:
            self.setup_maintenance_mode()
            return {"firing_status": "CRITICAL FAILURE", "reason": "Breech Friction Overload. Mode forced to MAINTENANCE."}
        
        return {
            "firing_status": "SUCCESSFUL 55mm DISCHARGE",
            "calculated_lead_deg": lead_correction,
            "inducted_fuze_time_sec": fuze_time,
            "recoil_force_kn": force_profile["force_kn"]
        }

async def engage_target_and_broadcast(gun: Gerat58StateEngine, cam: MechanicalBallisticCam, bridge: TriSystemBridge, target: Dict[str, Any]):
    """Fires the physical gun simulator and bridges the live telemetry over the network."""
    logging.info(f"Engaging Target: {target['target_class']} at {target['range']}m")
    
    # Process physical firing mechanics
    report = gun.process_firing_sequence(cam, target["range"], target["elevation"])
    logging.info(f"Gun Status: {report['firing_status']}")
    
    # If the gun successfully fired, bump the threat severity and broadcast to Univac Aegis
    if "SUCCESSFUL" in report["firing_status"]:
        target["threat_level"] = 10  # Active weapon discharge priority
        await bridge.broadcast_target_lock(target)
    else:
        logging.warning(f"Engagement Aborted: {report.get('reason')}")
        
    return report

async def run_museum_interactive_demo():
    print("\n==================================================================")
    print(" RHEINMETALL GERAT 58 & UNIVAC AEGIS INTERACTIVE ENGINE DEPLOYED")
    print("==================================================================\n")
    
    # 1. Initialize Hardware Components
    gun = Gerat58StateEngine()
    ballistic_cam = MechanicalBallisticCam()
    
    # 2. Initialize the Network Bridge
    aegis_endpoint = "http://api.revolutionary.technology:8000/univac-aegis/ingest"
    aviation_endpoint = "http://api.revolutionary.technology:8001/aviation-telemetry/ingest"
    bridge = TriSystemBridge(aegis_endpoint, aviation_endpoint, node_id="KDO58-Museum-01")
    await bridge.initialize()
    
    try:
        # 3. Setup Weapon for Combat
        logging.info("DEPLOYING WEAPON SYSTEM")
        gun.actuate_control("13_travel_lock_clamp", False)
        gun.actuate_control("14_outrigger_jacks", "DEPLOYED")
        gun.change_system_mode("COMBAT")
        gun.actuate_control("2_safety_selector", "EINZEL")
        
        # 4. Simulate a live radar track coming from the HPC swarm
        simulated_target = {
            "azimuth": 145.2,
            "elevation": 30.5,
            "range": 5000.0,
            "velocity_knots": 480.0,
            "altitude_feet": 24000.0,
            "heading": 330.0,
            "v_speed": -500.0,
            "target_class": "HEAVY_BOMBER",
            "threat_level": 8
        }
        
        # 5. Fire round 1 (Requires manual pneumatic charge first)
        gun.actuate_control("3_pneumatic_charging_lever", True)
        await engage_target_and_broadcast(gun, ballistic_cam, bridge, simulated_target)
        await asyncio.sleep(1.0)
        
        # 6. Update target kinematics and fire round 2
        simulated_target["range"] = 4800.0
        simulated_target["elevation"] = 32.0
        gun.actuate_control("3_pneumatic_charging_lever", True)
        await engage_target_and_broadcast(gun, ballistic_cam, bridge, simulated_target)

    finally:
        # 7. Ensure network sockets are safely closed on shutdown
        await bridge.shutdown()

if __name__ == "__main__":
    # The asyncio event loop correctly manages both the gun physics and the network bridging
    asyncio.run(run_museum_interactive_demo())
