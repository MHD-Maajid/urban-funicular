# Handling field map

Source of truth:

- Live struct: `chandling-svr/src/HandlingStruct.h` (`tHandlingData`)
- Pawn names: `chandling-svr/chandlingsvr.inc`
- Ranges: `chandling-svr/src/HandlingEnum.cpp` (`IsValidHandlingValue`)
- SASDK size note: `CHandlingData` is **0xE0 (224 bytes)** at `ms_vehicleHandling` `0xC2B9DC`
- Vehicle health: SASDK `CVehicle::m_fHealth` at **+0x4C0**. Full = **1000**. `<= 0` wrecks the car.

JSON numbers are **handling.cfg / CHandling numbers**, not converted internal game units.

## Columns written to `data/handling.cfg`

| # | JSON key | Pawn `CHandlingAttrib` | Type | Range used by generator |
|---|----------|------------------------|------|-------------------------|
| 1 | `replace.handling_id` | `HANDL_IDENTIFIER` (read-only) | string | 1–8 `A-Z0-9_` |
| 2 | `mass` | `HANDL_FMASS` | float | 1–50000 |
| 3 | `turn_mass` | `HANDL_FTURNMASS` | float | 0–50000 |
| 4 | `drag_multiplier` | `HANDL_FDRAGMULTIPLIER` | float | -200–200 |
| 5–7 | `centre_of_mass_x/y/z` | `HANDL_CENTREOFMASS_*` | float | -10–10 |
| 8 | `percent_submerged` | `HANDL_NPERCENTSUBMERGED` | byte | 1–255 |
| 9 | `traction_multiplier` | `HANDL_FTRACTIONMULTIPLIER` | float | -100–100 |
| 10 | `traction_loss` | `HANDL_FTRACTIONLOSS` | float | 0–100 |
| 11 | `traction_bias` | `HANDL_FTRACTIONBIAS` | float | 0–1 |
| 12 | `number_of_gears` | `HANDL_TR_NNUMBEROFGEARS` | byte | 1–5 |
| 13 | `max_velocity` | `HANDL_TR_FMAXVELOCITY` | float | 0.1–10000 |
| 14 | `engine_acceleration` | `HANDL_TR_FENGINEACCELERATION` | float | 0–10000 |
| 15 | `engine_inertia` | `HANDL_TR_FENGINEINERTIA` | float | -1000–1000, not 0 |
| 16 | `drive_type` | `HANDL_TR_NDRIVETYPE` | char | `R` `F` `4` |
| 17 | `engine_type` | `HANDL_TR_NENGINETYPE` | char | `P` `D` `E` |
| 18 | `brake_deceleration` | `HANDL_FBRAKEDECELERATION` | float | 0.1–10000 |
| 19 | `brake_bias` | `HANDL_FBRAKEBIAS` | float | 0–1 |
| 20 | `abs` | `HANDL_BABS` | 0/1 | 0 or 1 |
| 21 | `steering_lock` | `HANDL_FSTEERINGLOCK` | float | 0–360 |
| 22 | `suspension_force_level` | `HANDL_FSUSPENSIONFORCELEVEL` | float | 0–600 |
| 23 | `suspension_damping_level` | `HANDL_FSUSPENSIONDAMPINGLEVEL` | float | 0–600 |
| 24 | `suspension_high_spd_com_damp` | `HANDL_FSUSPENSIONHIGHSPDCOMDAMP` | float | 0–600 |
| 25 | `suspension_upper_limit` | `HANDL_FSUSPENSIONUPPERLIMIT` | float | -50–50 |
| 26 | `suspension_lower_limit` | `HANDL_FSUSPENSIONLOWERLIMIT` | float | -50–50 |
| 27 | `suspension_bias` | `HANDL_FSUSPENSIONBIAS` | float | 0–1 |
| 28 | `suspension_anti_dive` | `HANDL_FSUSPENSIONANTIDIVEMULT` | float | 0–30 |
| 29 | `seat_offset_distance` | `HANDL_FSEATOFFSETDISTANCE` | float | -20–20 |
| 30 | `collision_damage_multiplier` | `HANDL_FCOLLISIONDAMAGEMULT` | float | 0–10 |
| 31 | `monetary_value` | `HANDL_NMONETARYVALUE` (read-only in plugin) | uint | >= 1 |
| 32 | `model_flags` | `HANDL_MODELFLAGS` | hex flags | see below |
| 33 | `handling_flags` | `HANDL_HANDLINGFLAGS` | hex flags | see below |
| 34 | `front_lights` | `HANDL_FRONTLIGHTS` | 0–3 | LONG SMALL BIG TALL |
| 35 | `rear_lights` | `HANDL_REARLIGHTS` | 0–3 | LONG SMALL BIG TALL |
| 36 | `anim_group` | `HANDL_ANIMGROUP` (read-only in plugin) | byte | 0–255 |

CHandling cannot **set** identifier, monetary value, or anim group at runtime. They still belong in `handling.cfg` for single-player GTA:SA.

## What to twist for “feel”

| Want | Raise | Lower |
|------|-------|-------|
| Faster acceleration | `engine_acceleration`, add `1G_BOOST` / `2G_BOOST` | `engine_inertia`, `drag_multiplier`, `mass` |
| Higher top speed | `max_velocity`, add `USE_MAXSP_LIMIT` if it overshoots | `drag_multiplier` |
| Stronger braking | `brake_deceleration` | — |
| Less nose dive under brakes | `suspension_anti_dive`, `brake_bias` toward 0.5 | `brake_bias` near 1.0 |
| Tougher body | lower `collision_damage_multiplier`, higher `damage.spawn_health` | — |
| Fragile | `collision_damage_multiplier` toward 1.0+ | `spawn_health` |
| Less spin | `traction_multiplier`, `traction_loss` | COM Y too far forward/back |
| Heavier SUV | `mass`, `turn_mass` | `engine_acceleration` |

Stock Infernus (`411`) uses accel **12.0**, brake **11.0**, damage mult **0.72**.
Stock Sultan (`560`) uses accel **11.2**, brake **10.0**, damage mult **0.60**.
Stock Landstalker (`400`) uses accel **10.0**, brake **6.2**, damage mult **0.23**.

## Flag names (JSON arrays)

Model flags (`handling.model_flags`): `IS_VAN`, `IS_BUS`, `IS_LOW`, `IS_BIG`, `REVERSE_BONNET`, `HANGING_BOOT`, `TAILGATE_BOOT`, `NOSWING_BOOT`, `NO_DOORS`, `TANDEM_SEATS`, `SIT_IN_BOAT`, `CONVERTIBLE`, `NO_EXHAUST`, `DOUBLE_EXHAUST`, `NO1FPS_LOOK_BEHIND`, `FORCE_DOOR_CHECK`, `AXLE_F_NOTILT`, `AXLE_F_SOLID`, `AXLE_F_MCPHERSON`, `AXLE_F_REVERSE`, `AXLE_R_NOTILT`, `AXLE_R_SOLID`, `AXLE_R_MCPHERSON`, `AXLE_R_REVERSE`, `IS_BIKE`, `IS_HELI`, `IS_PLANE`, `IS_BOAT`, `BOUNCE_PANELS`, `DOUBLE_RWHEELS`, `FORCE_GROUND_CLEARANCE`, `IS_HATCHBACK`.

Handling flags (`handling.handling_flags`): `1G_BOOST`, `2G_BOOST`, `NPC_ANTI_ROLL`, `NPC_NEUTRAL_HANDL`, `NO_HANDBRAKE`, `STEER_REARWHEELS`, `HB_REARWHEEL_STEER`, `ALT_STEER_OPT`, `WHEEL_F_NARROW2`, `WHEEL_F_NARROW`, `WHEEL_F_WIDE`, `WHEEL_F_WIDE2`, `WHEEL_R_NARROW2`, `WHEEL_R_NARROW`, `WHEEL_R_WIDE`, `WHEEL_R_WIDE2`, `HYDRAULIC_GEOM`, `HYDRAULIC_INST`, `HYDRAULIC_NONE`, `NOS_INST`, `OFFROAD_ABILITY`, `OFFROAD_ABILITY2`, `HALOGEN_LIGHTS`, `PROC_REARWHEEL_1ST`, `USE_MAXSP_LIMIT`, `LOW_RIDER`, `STREET_RACER`, `SWINGING_CHASSIS`.

You may also pass a hex string (`"40002004"`) or an integer.
