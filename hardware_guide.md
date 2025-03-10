# Comprehensive Hardware Construction and Electronics Installation Guide

This guide provides detailed, step-by-step instructions for building the Robot Mower Advanced hardware platform and installing all required electronics. It covers everything from chassis preparation to final testing.

## Table of Contents

- [Complete Bill of Materials](#complete-bill-of-materials)
- [Tools Required](#tools-required)
- [Mechanical Construction](#mechanical-construction)
  - [Chassis Preparation](#chassis-preparation)
  - [Motor Mounting](#motor-mounting)
  - [Wheel Assembly](#wheel-assembly)
  - [Cutting System Assembly](#cutting-system-assembly)
  - [Electronics Enclosure](#electronics-enclosure)
- [Electronics Installation](#electronics-installation)
  - [Power System Wiring](#power-system-wiring)
  - [Motor Controller Wiring](#motor-controller-wiring)
  - [Sensor Installation](#sensor-installation)
  - [Raspberry Pi Setup](#raspberry-pi-setup)
  - [Detailed Wiring Diagrams](#detailed-wiring-diagrams)
- [Component Testing](#component-testing)
- [System Integration](#system-integration)
- [Troubleshooting](#troubleshooting)

## Complete Bill of Materials

### Chassis and Mechanical Components

| Component | Quantity | Recommended Model | Alt. Model | Est. Price (USD) |
|-----------|----------|-------------------|------------|-----------------|
| Mower Chassis Base | 1 | Plastic HDPE Sheet 6mm (80×60cm) | Aluminum 5mm | $35-50 |
| Drive Motors | 2 | DC Gearmotor 12V 200RPM (Pololu #4758) | uxcell 12V 100RPM | $25-40 each |
| Cutting Motor | 1 | Brushless Motor 24V 250W 2800RPM | DC Motor 12V 150W | $40-60 |
| Motor Mounts | 2 | Pololu Bracket #2676 | 3D-printed ABS | $8-12 each |
| Wheels | 2 | 200mm Pneumatic (6206-2RS bearings) | Solid Rubber 180mm | $15-25 each |
| Cutting Blade | 1 | 10" 3-tooth Steel Blade | 8" 4-tooth Blade | $15-20 |
| Blade Disc | 1 | Aluminum 5mm (20cm diameter) | 3D-printed PLA+ | $20-25 |
| Castor Wheel | 1 | 75mm Swivel Castor with Bearings | 50mm Solid Castor | $12-15 |
| Chassis Standoffs | 12 | M3 30mm Hex Standoffs | M3 Nylon Standoffs | $0.50 each |
| Enclosure | 1 | Hammond 1590XXLBK (222×146×55mm) | IP65 ABS Enclosure | $30-40 |
| Screws & Fasteners | Various | M3, M4, M5 Stainless Steel Set | Mixed Bolt Assortment | $15-20 |

### Electronics Components

| Component | Quantity | Recommended Model | Alt. Model | Est. Price (USD) |
|-----------|----------|-------------------|------------|-----------------|
| Raspberry Pi | 1 | Pi 4 Model B 8GB | Pi 4 Model B 4GB | $75-85 |
| microSD Card | 1 | SanDisk Extreme Pro 64GB | Samsung EVO 32GB | $15-20 |
| IMU Sensor | 1 | MPU-9250 | MPU-6050 | $8-15 |
| Ultrasonic Sensors | 6 | HC-SR04P (5V) | JSN-SR04T (Waterproof) | $2-4 each |
| GPS Module | 1 | NEO-M8N with Antenna | NEO-6M | $20-35 |
| Camera Module | 1 | Raspberry Pi Camera V3 | Arducam 8MP | $25-35 |
| Motor Driver (Drive) | 1 | Cytron MDD10A | L298N Module | $20-30 |
| Motor Driver (Cutting) | 1 | BTS7960 43A | MOSFET IRF3205 + Driver | $15-20 |
| DC-DC Converter | 1 | DROK Buck Converter 5A | LM2596 Module | $8-15 |
| Power Switch | 1 | 16mm Waterproof Switch | Toggle Switch with Cover | $3-5 |
| Battery (LiFePO4) | 1 | 12.8V 20Ah with BMS | 12V 18Ah SLA | $120-180 |
| Voltage Monitor | 1 | INA219 Current/Voltage Sensor | Voltage Divider Module | $3-8 |
| E-Stop Button | 1 | 22mm Red Mushroom Emergency Stop | 16mm E-Stop Button | $5-10 |
| Wire (Power) | 3m | 14AWG Silicone Wire (Red/Black) | 16AWG Stranded | $10-15 |
| Wire (Signal) | 5m | 22AWG Stranded (Various Colors) | 24AWG Ribbon Cable | $10-15 |
| Connectors Kit | 1 | JST Connector Kit with Crimping Tool | Dupont Connector Kit | $15-25 |
| Wheel Encoders | 2 | LM393 Speed Sensor Module | AS5600 Magnetic Encoder | $3-8 each |
| Rain Sensor | 1 | YL-83 Rain Detection Module | FC-37 Module | $3-5 |
| PCB Terminal Blocks | 10 | 2-pin & 3-pin 5.08mm Pitch | Screw Terminal Block Set | $1-2 each |

### Tools Required

* Soldering iron (40-60W) with solder wire
* Wire strippers and cutters
* Crimping tool for JST/Dupont connectors
* Heat shrink tubing assortment
* Digital multimeter
* Drill with drill bit set
* Screwdriver set (Philips and flathead)
* Allen key set (hex wrenches)
* Hobby knife or rotary tool (for enclosure modifications)
* Small files set
* Thread-locking compound (medium strength)
* Heat gun or lighter (for heat shrink)
* Electrical tape
* Cable ties (various sizes)
* Third-hand tool or PCB vise

## Mechanical Construction

### Chassis Preparation

#### 1. Chassis Base Cutting

1. Mark the HDPE sheet (80cm × 60cm) according to this cutting template:
   ```
   ┌──────────────────────────────────┐
   │                                  │
   │                                  │
   │       [Drive Motors Area]        │
   │                                  │
   │                                  │
   ├──────────────────────────────────┤
   │                                  │
   │       [Cutting Blade Area]       │
   │                                  │
   └──────────────────────────────────┘
   ```

2. Cut the HDPE sheet along the marked lines using a jigsaw with a fine-tooth blade.
   * Ensure all edges are smooth by sanding with 220-grit sandpaper.
   * Round all corners with a 10mm radius for safety.

3. Drill mounting holes according to the following pattern:
   * Drive motor mounting: 4× M4 holes (matching your motor mount pattern)
   * Electronics enclosure: 4× M3 holes in a rectangular pattern
   * Castor wheel: 4× M5 holes in the front center
   * Cutting motor: 4× M5 holes in a square pattern (dependent on motor size)

#### 2. Chassis Reinforcement

1. Cut aluminum angle (20mm × 20mm) to match the perimeter of the chassis.
2. Drill matching holes in the aluminum angle.
3. Attach the angle to the perimeter using M3 bolts and nuts.
4. Apply thread locker to all bolts.

### Motor Mounting

#### 1. Drive Motor Installation

1. Position the motor mounts at the marked locations.
2. Secure motor mounts to the chassis using M4 bolts, washers, and nylon lock nuts.
3. Insert drive motors into the mounts:
   * Orient the motors so the output shafts align with the planned wheel positions.
   * Secure motors to mounts using the hardware provided with the motor brackets.
4. Apply thread locker to all bolts and leave to dry for 24 hours.

**Detailed motor mount spacing diagram:**
```
          ┌─────────────┐
          │             │
          │   CHASSIS   │
          │             │
┌────┐    │             │    ┌────┐
│ LM │◄───┼─── 40cm ────┼───►│ RM │
└────┘    │             │    └────┘
          │             │
          └─────────────┘
```
LM = Left Motor, RM = Right Motor

#### 2. Cutting Motor Installation

1. Position the cutting motor mount at the center front of the chassis.
2. Secure the mount with M5 bolts, washers, and nylon lock nuts.
3. Install the motor with the shaft pointing downward.
4. Apply thread locker to all bolts.

### Wheel Assembly

#### 1. Drive Wheel Preparation

1. For each drive wheel:
   * Insert the 6206-2RS bearings into the wheel hub.
   * Ensure the bearings are fully seated and rotate freely.

2. Prepare the wheel adapters to match your motor shaft:
   * For D-shaft motors: Use D-shaft hubs (Pololu #1996)
   * For round shaft motors: Use shaft collars with set screws

3. Secure the wheel adapter to the motor shaft:
   * Apply thread locker to set screws
   * Tighten firmly but do not over-torque

4. Mount wheels to the adapters:
   * Align the wheel evenly with the adapter
   * Secure with M5 bolts and washers
   * Verify that the wheel rotates freely without wobble

#### 2. Castor Wheel Installation

1. Position the castor wheel at the front center of the chassis.
2. Mark and drill 4× M5 mounting holes.
3. Attach the castor using M5 bolts, washers, and nylon lock nuts.
4. Check that the castor rotates and swivels freely.

### Cutting System Assembly

#### 1. Blade Disc Construction

1. From 5mm aluminum plate, cut a circular disc (200mm diameter).
2. Mark and drill the center hole to match your motor shaft size.
3. Drill 3 mounting holes for the cutting blade, positioned 120° apart at a radius of 75mm from center.
4. Drill and tap mounting holes for the blade.
5. Add counter-balance weights if necessary for smooth operation.

#### 2. Blade Installation

1. Place blade disc on the motor shaft.
2. Secure with a shaft collar or center bolt depending on your motor shaft type.
3. Mount the cutting blade to the disc using M5 bolts, washers, and nylon lock nuts.
4. Balance the assembly by adding small weights to the underside if necessary.
5. Verify that the blade assembly has about 25mm ground clearance.

#### 3. Blade Guard Installation

1. Cut a circular guard from 2mm aluminum sheet (250mm diameter).
2. Create vent holes or slits for grass discharge.
3. Bend edges downward (10mm) around the perimeter for additional strength.
4. Attach to the chassis using aluminum standoffs.
5. Ensure the guard fully covers the blade with a minimum 25mm clearance from blade tips.

### Electronics Enclosure

#### 1. Enclosure Preparation

1. Mark cutouts on the enclosure for:
   * USB and HDMI ports (if accessing the Raspberry Pi externally)
   * Power switch
   * Emergency stop button
   * Cable glands for motor and sensor wires
   * Optional: Status LEDs and display

2. Drill or cut the marked areas:
   * Use a step drill bit for circular holes
   * Use a rotary tool with cutting disc for rectangular openings
   * File edges smooth

3. Install cable glands (M12 size) for all external connections:
   * 2× for drive motor wires
   * 1× for cutting motor wires
   * 1× for sensor wires
   * 1× for power input

4. Mount the enclosure to the chassis:
   * Use vibration-dampening standoffs or rubber grommets
   * Secure with M3 bolts and washers

#### 2. Internal Mounting Plate

1. Cut a mounting plate from 3mm acrylic or aluminum to fit inside the enclosure.
2. Mark positions for:
   * Raspberry Pi mounting holes
   * Motor controller mounting holes
   * DC-DC converter
   * Terminal blocks
   * Additional electronics

3. Drill mounting holes (M2.5 or M3 as appropriate).

4. Install M3 standoffs for all components.

5. Secure the mounting plate inside the enclosure.

## Electronics Installation

### Power System Wiring

#### 1. Battery Installation

1. Create a secure battery compartment on the chassis:
   * Use foam padding to prevent movement
   * Ensure the battery is protected from impacts
   * Allow for adequate ventilation

2. Install the main power switch:
   * Wire between battery positive terminal and the system
   * Use 14AWG wire minimum
   * Add an inline 20A fuse for protection

3. Connect the battery:
   * Use XT60 or Anderson connectors for easy disconnection
   * Label connectors clearly
   * Install a battery monitor/gauge at the battery output

#### 2. Power Distribution

1. Create a power distribution block:
   * Use a PCB with terminal blocks
   * Alternative: Insulated bus bars

2. Wire the distribution with these outputs:
   * Drive motors: 12V/24V direct from battery (through motor controller)
   * Cutting motor: 12V/24V direct from battery (through separate controller)
   * Raspberry Pi: 5V regulated from DC-DC converter
   * Sensors: 5V regulated from DC-DC converter or from Raspberry Pi

3. Wire the DC-DC converter:
   * Input: Battery voltage (12V/24V)
   * Output: 5V regulated
   * Add capacitors to input (100μF) and output (470μF) for filtering
   * Heat-sink the converter if necessary

**Power distribution diagram:**
```
                   ┌───────────┐
                   │  Battery  │
                   │ 12V/24V   │
                   └─────┬─────┘
                         │
                    ┌────┴─────┐
                    │   Fuse   │
                    │   20A    │
                    └────┬─────┘
                         │
                   ┌─────┴──────┐
                   │   Switch   │
                   └─────┬──────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
    │   Drive   │  │  Cutting  │  │   DC-DC   │
    │Controller │  │ Controller│  │ Converter │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
    │   Drive   │  │  Cutting  │  │    5V     │
    │   Motors  │  │   Motor   │  │ Electronics│
    └───────────┘  └───────────┘  └───────────┘
```

### Motor Controller Wiring

#### 1. Drive Motor Controller

1. Mount the motor controller (Cytron MDD10A or similar) to the mounting plate using standoffs.

2. Connect power input:
   * VIN: Battery positive (via power switch and fuse)
   * GND: Battery negative
   * Use 14AWG silicone wire

3. Connect motor outputs:
   * M1A and M1B to left motor (via screw terminals)
   * M2A and M2B to right motor (via screw terminals)
   * Use 16AWG silicone wire
   * Add ferrite cores to motor wires to reduce noise

4. Connect control signals from Raspberry Pi:
   * PWM1: GPIO12 (left motor speed)
   * PWM2: GPIO13 (right motor speed)
   * DIR1: GPIO17 (left motor direction)
   * DIR2: GPIO22 (right motor direction)
   * GND: Connect to Raspberry Pi GND
   * Use 22AWG wire with heat shrink

#### 2. Cutting Motor Controller

1. Mount the BTS7960 or MOSFET controller to the mounting plate.

2. Connect power input:
   * VCC: Battery positive (via separate 30A fuse)
   * GND: Battery negative
   * Use 12AWG silicone wire

3. Connect motor output:
   * Motor+ and Motor- to cutting motor
   * Use 14AWG silicone wire
   * Add suppression capacitor (0.1μF) across motor terminals

4. Connect control signals from Raspberry Pi:
   * RPWM: GPIO24 (forward speed)
   * LPWM: GPIO25 (reverse speed, usually not used)
   * R_EN: GPIO23 (enable right side)
   * L_EN: GPIO23 (connect to same pin as R_EN)
   * GND: Connect to Raspberry Pi GND
   * Use 22AWG wire with heat shrink

### Sensor Installation

#### 1. Ultrasonic Sensors

1. Mount HC-SR04P sensors around the perimeter:
   * 2× front-facing (30° apart)
   * 1× each at 45° front-left and front-right
   * 1× each at rear-left and rear-right
   * Use 3D-printed brackets for mounting

2. Wire each sensor:
   * VCC: Connect to 5V from Raspberry Pi or DC-DC converter
   * GND: Connect to Raspberry Pi GND
   * TRIG: Connect to designated GPIO pin
   * ECHO: Connect to designated GPIO pin through a voltage divider:
     * 1kΩ resistor from ECHO to GPIO
     * 2kΩ resistor from GPIO to GND
   * Use 24AWG wire with connectors for easy removal

3. Route sensor cables:
   * Use cable channels or conduit on the chassis
   * Group wires and label them
   * Use heat-shrink at all junction points

**Ultrasonic sensor wiring diagram:**
```
                              ┌─────────────────┐
                              │   Raspberry Pi  │
                              │                 │
HC-SR04P                      │                 │
┌─────────┐    ┌──────────────┤ 5V          GND ├─────────┐
│         │    │              │                 │         │
│      VCC├────┘              │                 │         │
│         │                   │                 │         │
│      GND├───────────────────┤ GND             │         │
│         │                   │                 │         │
│     TRIG├───────────────────┤ GPIO (TRIG_PIN) │         │
│         │         ┌─────────┤ GPIO (ECHO_PIN) │         │
│     ECHO├─────────┤ 1kΩ     │                 │         │
└─────────┘         └─┬───────┤                 │         │
                      │       │                 │         │
                      │ 2kΩ   │                 │         │
                      └───────┤                 │         │
                              └─────────────────┘         │
                                                          │
                                                          │
                   ┌───────────────────────────────┐      │
                   │            Ground             ├──────┘
                   └───────────────────────────────┘
```

#### 2. IMU Installation

1. Mount the MPU-9250 (or MPU-6050) IMU:
   * Position at the center of the chassis
   * Orient so X-axis aligns with forward direction
   * Use rubber vibration isolation mounts

2. Wire the IMU:
   * VCC: Connect to 3.3V from Raspberry Pi
   * GND: Connect to Raspberry Pi GND
   * SCL: Connect to GPIO3 (I2C1 SCL)
   * SDA: Connect to GPIO2 (I2C1 SDA)
   * Use twisted pair wires for SCL and SDA
   * Keep wires short to reduce interference

#### 3. GPS Module Installation

1. Mount the GPS module:
   * Position antenna with clear view of the sky
   * Keep away from interference sources (motors, power wires)
   * Secure antenna with a bracket or mount

2. Wire the GPS:
   * VCC: Connect to 5V or 3.3V (depending on your module)
   * GND: Connect to Raspberry Pi GND
   * TX: Connect to GPIO15 (UART RX)
   * RX: Connect to GPIO14 (UART TX)
   * Use shielded cable if possible

#### 4. Wheel Encoders

1. Mount the encoders:
   * Position near the wheel hubs
   * Ensure proper alignment with encoder disk/magnet
   * Use 3D-printed brackets for mounting

2. Wire each encoder:
   * VCC: Connect to 5V from Raspberry Pi or DC-DC converter
   * GND: Connect to Raspberry Pi GND
   * Signal: Connect to designated GPIO pin
   * Use 24AWG wire with shielding
   * Include pull-up resistors if not integrated on the module

### Raspberry Pi Setup

#### 1. Raspberry Pi Mounting

1. Install the Raspberry Pi on the mounting plate:
   * Use M2.5 screws and spacers
   * Ensure adequate ventilation
   * Position with ports accessible

2. Connect cooling fan:
   * Mount fan on enclosure wall or directly above Pi
   * Wire to 5V and GND pins on the Raspberry Pi
   * Consider a temperature-controlled setup

#### 2. Core Connections

1. Connect Raspberry Pi power:
   * Use a high-quality DC-DC converter with 5V 3A output
   * Connect to USB-C port (Pi 4) or GPIO power pins
   * Add a power filter capacitor (1000μF) near the connection

2. Connect essential peripherals:
   * Optional: Small OLED display for status
   * Optional: Status LEDs for power, error, activity
   * Emergency stop button (connect to designated GPIO)

#### 3. GPIO Pin Assignments

The following pin mapping shows the GPIO connections to various components:

```
┌─────────────────────────────────────────┐
│               Raspberry Pi              │
└───┬───────────────────────────────┬─────┘
    │ GPIO Pins                     │
    │                               │
    ├─── GPIO2  (I2C1 SDA) ─────────┼──► IMU (SDA)
    ├─── GPIO3  (I2C1 SCL) ─────────┼──► IMU (SCL)
    │                               │
    ├─── GPIO5  ─────────────────┐  │
    ├─── GPIO6  ─────────────────┼──┼──► Ultrasonic Sensors (TRIG)
    ├─── GPIO16 ─────────────────┼──┼──► (using 6 different pins)
    ├─── GPIO19 ─────────────────┘  │
    │                               │
    ├─── GPIO26 ─────────────────┐  │
    ├─── GPIO20 ─────────────────┼──┼──► Ultrasonic Sensors (ECHO)
    ├─── GPIO21 ─────────────────┼──┼──► (using 6 different pins)
    ├─── GPIO7  ─────────────────┘  │
    │                               │
    ├─── GPIO17 ─────────────────┐  │
    ├─── GPIO18 ─────────────────┼──┼──► Left Motor Control
    ├─── GPIO22 ─────────────────┼──┼──► Right Motor Control
    ├─── GPIO23 ─────────────────┘  │
    │                               │
    ├─── GPIO12 (PWM0) ────────────┼──► Left Motor Speed
    ├─── GPIO13 (PWM1) ────────────┼──► Right Motor Speed
    │                               │
    ├─── GPIO24 ─────────────────┐  │
    ├─── GPIO25 ─────────────────┼──┼──► Cutting Motor Control
    │                               │
    ├─── GPIO14 (UART TX) ─────────┼──► GPS Module (RX)
    ├─── GPIO15 (UART RX) ─────────┼──► GPS Module (TX)
    │                               │
    └───────────────────────────────┘
```

### Detailed Wiring Diagrams

#### Main Power Circuit Diagram

```
Battery Positive ──┬── 20A Fuse ── Main Switch ─┬── MDD10A VIN ── Drive Motors
                   │                            │
                   │                            ├── BTS7960 VCC ── Cutting Motor
                   │                            │
                   │                            └── DC-DC Input ── 5V System
                   │
Battery Negative ──┴────────────────────────────┬── MDD10A GND
                                                │
                                                ├── BTS7960 GND
                                                │
                                                └── DC-DC GND ── System GND
```

#### Control Signal Wiring Diagram

```
Raspberry Pi GPIO17 ────── MDD10A DIR1 (Left Dir)
Raspberry Pi GPIO22 ────── MDD10A DIR2 (Right Dir)
Raspberry Pi GPIO12 ────── MDD10A PWM1 (Left Speed)
Raspberry Pi GPIO13 ────── MDD10A PWM2 (Right Speed)
Raspberry Pi GPIO24 ────── BTS7960 RPWM (Cutting Motor Speed)
Raspberry Pi GPIO23 ────── BTS7960 R_EN & L_EN (Enable)
Raspberry Pi GND ─────┬─── MDD10A GND
                      │
                      └─── BTS7960 GND
```

## Component Testing

### 1. Power System Verification

1. **Before connecting any components**:
   * Measure battery voltage with a multimeter
   * Verify DC-DC converter output voltage (should be 5V ±0.1V)
   * Check for shorts between power and ground

2. **Power Distribution Testing**:
   * Connect the power switch and fuse
   * Measure voltage at all distribution points
   * Verify that the power switch properly cuts all power

### 2. Motor Controller Testing

1. **Drive Motor Controller**:
   * Disconnect motors
   * Apply power to the controller
   * Verify LED indicators function correctly
   * Test control signals with jumper wires
   * Measure output voltage when activated

2. **Cutting Motor Controller**:
   * Disconnect cutting motor
   * Apply power to the controller
   * Test control signals
   * Verify that the E-stop button cuts power to the motor controller

### 3. Sensor Verification

1. **Ultrasonic Sensors**:
   * Power up the sensors
   * Use a multimeter to verify correct voltage levels
   * Check ECHO pin voltage changes when obstacle detected

2. **IMU Sensor**:
   * Run I2C detection: `sudo i2cdetect -y 1`
   * Verify the IMU address appears (typically 0x68)

3. **GPS Module**:
   * Check power LEDs on the module
   * Run a test UART communication

### 4. Raspberry Pi Setup Verification

1. Run the test script to check all connected hardware:
   ```bash
   cd ~/robot-mower-advanced
   python3 utils/hardware_test.py
   ```

2. Check GPIO pin status with:
   ```bash
   gpio readall
   ```

## System Integration

### 1. Final Assembly Checklist

- [ ] All mechanical components securely fastened
- [ ] All electrical connections properly soldered/crimped and insulated
- [ ] Wire routing neat and away from moving parts
- [ ] All connectors labeled
- [ ] Battery securely mounted and connected
- [ ] Electronics enclosure properly sealed
- [ ] E-stop button installed and tested
- [ ] Software installed on Raspberry Pi
- [ ] System configuration completed

### 2. Final Testing

1. **Power-On Test**:
   * Power on the system with the cutting mechanism disabled
   * Verify all sensors initialize correctly
   * Check system status via SSH or connected display

2. **Movement Test**:
   * Lift the mower so wheels are free to rotate
   * Run the motor test program at low speed
   * Verify proper directional control

3. **Cutting System Test**:
   * Secure the mower on blocks with cutting blade clear of all obstacles
   * Test cutting motor at varying speeds
   * Check emergency stop functionality

4. **Full System Test**:
   * Run the enclosed test area mode
   * Verify obstacle detection works correctly
   * Check navigation systems function properly

## Troubleshooting

### Common Hardware Issues

1. **Motor Not Running**:
   * Check power connections
   * Verify motor controller outputs with multimeter
   * Inspect for loose wires or poor crimps
   * Check GPIO pin assignments in config

2. **Sensors Not Working**:
   * Verify 5V supply voltage
   * Check GPIO pin assignments in software
   * For Ultrasonic: ensure voltage divider is correctly installed
   * For IMU: check I2C address and connections

3. **Raspberry Pi Instability**:
   * Check power supply voltage (should be 5V ±0.25V)
   * Verify cooling is adequate
   * Run memory and CPU tests
   * Check for undervoltage warnings in system log

4. **Poor Motor Performance**:
   * Inspect mechanical alignment
   * Check for binding in the drive train
   * Verify voltage at the motor under load
   * Check PWM frequency settings

5. **Battery Issues**:
   * Measure voltage under no load and under load
   * Check for loose connections
   * Verify battery management system is functioning
   * Ensure proper charging between uses

### Advanced Diagnostics

1. **GPIO Signal Analysis**:
   * Use an oscilloscope to verify PWM signals
   * Check signal integrity of I2C and UART communications
   * Verify ultrasonic sensor timing

2. **Current Consumption Analysis**:
   * Measure current draw of individual components
   * Monitor total system current during operation
   * Identify abnormal power consumption

3. **Communication Debugging**:
   * Enable debug logging in the software
   * Monitor I2C and UART traffic
   * Check for packet loss or corruption in sensor data

---

**Safety Notes**:
- Always disconnect the battery before working on the electrical system
- Secure or remove the cutting blade during testing
- Wear safety glasses when working with tools
- Test the emergency stop function before each use
- Never operate the mower without proper safety guards in place
