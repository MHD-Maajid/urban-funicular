#!/usr/bin/env python3
"""
Convert a vehicle-generation JSON definition into GTA:SA handling.cfg /
vehicles.ide lines and a SA-MP CHandling filterscript.

Validation ranges match chandling-svr/src/HandlingEnum.cpp.
handling.cfg column order matches tHandlingData in HandlingStruct.h.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_IDS = ROOT / "data" / "vehicle-ids.json"

# RenderWare chunk IDs from include/sasdk/rw.hpp
RW_CLUMP = 0x001C
RW_TEX_DICTIONARY = 0x0021
COL_MAGICS = {b"COL2", b"COLL", b"COL3"}

MODEL_FLAGS: dict[str, int] = {
    "IS_VAN": 0x1,
    "IS_BUS": 0x2,
    "IS_LOW": 0x4,
    "IS_BIG": 0x8,
    "REVERSE_BONNET": 0x10,
    "HANGING_BOOT": 0x20,
    "TAILGATE_BOOT": 0x40,
    "NOSWING_BOOT": 0x80,
    "NO_DOORS": 0x100,
    "TANDEM_SEATS": 0x200,
    "SIT_IN_BOAT": 0x400,
    "CONVERTIBLE": 0x800,
    "NO_EXHAUST": 0x1000,
    "DOUBLE_EXHAUST": 0x2000,
    "NO1FPS_LOOK_BEHIND": 0x4000,
    "FORCE_DOOR_CHECK": 0x8000,
    "AXLE_F_NOTILT": 0x10000,
    "AXLE_F_SOLID": 0x20000,
    "AXLE_F_MCPHERSON": 0x40000,
    "AXLE_F_REVERSE": 0x80000,
    "AXLE_R_NOTILT": 0x100000,
    "AXLE_R_SOLID": 0x200000,
    "AXLE_R_MCPHERSON": 0x400000,
    "AXLE_R_REVERSE": 0x800000,
    "IS_BIKE": 0x1000000,
    "IS_HELI": 0x2000000,
    "IS_PLANE": 0x4000000,
    "IS_BOAT": 0x8000000,
    "BOUNCE_PANELS": 0x10000000,
    "DOUBLE_RWHEELS": 0x20000000,
    "FORCE_GROUND_CLEARANCE": 0x40000000,
    "IS_HATCHBACK": 0x80000000,
}

HANDLING_FLAGS: dict[str, int] = {
    "1G_BOOST": 0x1,
    "2G_BOOST": 0x2,
    "NPC_ANTI_ROLL": 0x4,
    "NPC_NEUTRAL_HANDL": 0x8,
    "NO_HANDBRAKE": 0x10,
    "STEER_REARWHEELS": 0x20,
    "HB_REARWHEEL_STEER": 0x40,
    "ALT_STEER_OPT": 0x80,
    "WHEEL_F_NARROW2": 0x100,
    "WHEEL_F_NARROW": 0x200,
    "WHEEL_F_WIDE": 0x400,
    "WHEEL_F_WIDE2": 0x800,
    "WHEEL_R_NARROW2": 0x1000,
    "WHEEL_R_NARROW": 0x2000,
    "WHEEL_R_WIDE": 0x4000,
    "WHEEL_R_WIDE2": 0x8000,
    "HYDRAULIC_GEOM": 0x10000,
    "HYDRAULIC_INST": 0x20000,
    "HYDRAULIC_NONE": 0x40000,
    "NOS_INST": 0x80000,
    "OFFROAD_ABILITY": 0x100000,
    "OFFROAD_ABILITY2": 0x200000,
    "HALOGEN_LIGHTS": 0x400000,
    "PROC_REARWHEEL_1ST": 0x800000,
    "USE_MAXSP_LIMIT": 0x1000000,
    "LOW_RIDER": 0x2000000,
    "STREET_RACER": 0x4000000,
    "SWINGING_CHASSIS": 0x10000000,
}

LIGHTS = {"LONG": 0, "SMALL": 1, "BIG": 2, "TALL": 3}

FLOAT_RANGES = {
    "mass": (1.0, 50000.0),
    "turn_mass": (0.0, 50000.0),
    "drag_multiplier": (-200.0, 200.0),
    "centre_of_mass_x": (-10.0, 10.0),
    "centre_of_mass_y": (-10.0, 10.0),
    "centre_of_mass_z": (-10.0, 10.0),
    "traction_multiplier": (-100.0, 100.0),
    "traction_loss": (0.0, 100.0),
    "traction_bias": (0.0, 1.0),
    "max_velocity": (0.1, 10000.0),
    "engine_acceleration": (0.0, 10000.0),
    "brake_deceleration": (0.1, 10000.0),
    "brake_bias": (0.0, 1.0),
    "steering_lock": (0.0, 360.0),
    "suspension_force_level": (0.0, 600.0),
    "suspension_damping_level": (0.0, 600.0),
    "suspension_high_spd_com_damp": (0.0, 600.0),
    "suspension_upper_limit": (-50.0, 50.0),
    "suspension_lower_limit": (-50.0, 50.0),
    "suspension_bias": (0.0, 1.0),
    "suspension_anti_dive": (0.0, 30.0),
    "seat_offset_distance": (-20.0, 20.0),
    "collision_damage_multiplier": (0.0, 10.0),
}

REQUIRED_HANDLING = [
    "mass",
    "turn_mass",
    "drag_multiplier",
    "centre_of_mass_x",
    "centre_of_mass_y",
    "centre_of_mass_z",
    "percent_submerged",
    "traction_multiplier",
    "traction_loss",
    "traction_bias",
    "number_of_gears",
    "max_velocity",
    "engine_acceleration",
    "engine_inertia",
    "drive_type",
    "engine_type",
    "brake_deceleration",
    "brake_bias",
    "abs",
    "steering_lock",
    "suspension_force_level",
    "suspension_damping_level",
    "suspension_high_spd_com_damp",
    "suspension_upper_limit",
    "suspension_lower_limit",
    "suspension_bias",
    "suspension_anti_dive",
    "seat_offset_distance",
    "collision_damage_multiplier",
    "monetary_value",
    "front_lights",
    "rear_lights",
    "anim_group",
]


class VehicleError(Exception):
    pass


def load_ids() -> dict[str, Any]:
    with DATA_IDS.open(encoding="utf-8") as f:
        return json.load(f)["models"]


def parse_flags(value: Any, table: dict[str, int], label: str) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if isinstance(value, str):
        s = value.strip()
        if s.lower().startswith("0x"):
            return int(s, 16) & 0xFFFFFFFF
        if re.fullmatch(r"[0-9A-Fa-f]+", s):
            return int(s, 16) & 0xFFFFFFFF
        raise VehicleError(f"{label}: unknown string '{value}'")
    if isinstance(value, list):
        bits = 0
        for item in value:
            key = str(item).upper().replace("MFLAG_", "").replace("HFLAG_", "")
            if key not in table:
                raise VehicleError(f"{label}: unknown flag '{item}'")
            bits |= table[key]
        return bits & 0xFFFFFFFF
    raise VehicleError(f"{label}: expected int, hex string, or list of names")


def parse_lights(value: Any, label: str) -> int:
    if isinstance(value, int):
        if value not in (0, 1, 2, 3):
            raise VehicleError(f"{label}: lights must be 0-3 or LONG/SMALL/BIG/TALL")
        return value
    key = str(value).upper()
    if key not in LIGHTS:
        raise VehicleError(f"{label}: lights must be 0-3 or LONG/SMALL/BIG/TALL")
    return LIGHTS[key]


def require(obj: dict, key: str, where: str) -> Any:
    if key not in obj:
        raise VehicleError(f"missing '{where}.{key}'")
    return obj[key]


def in_range(name: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise VehicleError(f"{name}={value} is outside [{lo}, {hi}] (chandling-svr ranges)")


def validate(doc: dict[str, Any], ids: dict[str, Any]) -> dict[str, Any]:
    meta = require(doc, "meta", "root")
    replace = require(doc, "replace", "root")
    handling = require(doc, "handling", "root")
    assets = doc.get("assets") or {}
    ide = doc.get("ide") or {}

    name = str(require(meta, "name", "meta")).strip()
    if not name:
        raise VehicleError("meta.name is empty")
    slug = str(meta.get("slug") or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))
    if not slug:
        raise VehicleError("could not build a slug from meta.name")

    model_id = int(require(replace, "model_id", "replace"))
    if model_id < 400 or model_id > 611:
        raise VehicleError(f"replace.model_id={model_id} is not a SA-MP vehicle (400-611)")
    stock = ids[str(model_id)]
    keep_names = bool(replace.get("keep_stock_filenames", True))
    handling_id = str(replace.get("handling_id") or stock["handling"]).upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", handling_id):
        raise VehicleError(
            f"handling_id '{handling_id}' must be 1-8 chars A-Z 0-9 _ (handling.cfg identifier)"
        )

    for key in REQUIRED_HANDLING:
        if key not in handling:
            raise VehicleError(f"missing handling.{key}")

    for key, (lo, hi) in FLOAT_RANGES.items():
        in_range(f"handling.{key}", float(handling[key]), lo, hi)

    inertia = float(handling["engine_inertia"])
    if not (-1000.0 <= inertia <= 1000.0) or inertia == 0.0:
        raise VehicleError("handling.engine_inertia must be in [-1000, 1000] and not 0")

    gears = int(handling["number_of_gears"])
    if not (1 <= gears <= 5):
        raise VehicleError("handling.number_of_gears must be 1-5 (chandling-svr limit)")

    drive = str(handling["drive_type"]).upper()
    if drive not in ("R", "F", "4"):
        raise VehicleError("handling.drive_type must be R (RWD), F (FWD), or 4 (AWD)")

    engine = str(handling["engine_type"]).upper()
    if engine not in ("P", "D", "E"):
        raise VehicleError("handling.engine_type must be P (petrol), D (diesel), or E (electric)")

    percent = int(handling["percent_submerged"])
    if not (1 <= percent <= 255):
        raise VehicleError("handling.percent_submerged must be 1-255")

    abs_flag = handling["abs"]
    if abs_flag not in (0, 1, False, True):
        raise VehicleError("handling.abs must be 0 or 1")
    abs_flag = 1 if abs_flag in (1, True) else 0

    anim = int(handling["anim_group"])
    if not (0 <= anim <= 255):
        raise VehicleError("handling.anim_group must be 0-255")

    money = int(handling["monetary_value"])
    if money < 1:
        raise VehicleError("handling.monetary_value must be >= 1")

    model_flags = parse_flags(handling.get("model_flags", 0), MODEL_FLAGS, "handling.model_flags")
    handling_flags = parse_flags(
        handling.get("handling_flags", 0), HANDLING_FLAGS, "handling.handling_flags"
    )
    front_lights = parse_lights(handling["front_lights"], "handling.front_lights")
    rear_lights = parse_lights(handling["rear_lights"], "handling.rear_lights")

    dff_name = stock["dff"] if keep_names else str(ide.get("model_name") or slug)[:23]
    txd_name = stock["dff"] if keep_names else str(ide.get("txd_name") or dff_name)[:23]
    if not re.fullmatch(r"[A-Za-z0-9_]+", dff_name) or not re.fullmatch(r"[A-Za-z0-9_]+", txd_name):
        raise VehicleError("DFF/TXD names must be letters, digits, underscore only")

    veh_type = str(ide.get("type") or stock["class"])
    allowed_types = {"car", "mtruck", "quad", "boat", "train", "heli", "plane", "bike", "bmx", "trailer"}
    if veh_type not in allowed_types:
        raise VehicleError(f"ide.type '{veh_type}' is not a vehicles.ide type")

    game_name = str(ide.get("game_name") or handling_id)[:8]
    anims = str(ide.get("anims") or "null")
    veh_class = str(ide.get("vehicle_class") or "normal")
    frequency = int(ide.get("frequency", 10))
    ide_flags = int(ide.get("flags", 0))
    comprules = int(ide.get("comprules", 0))
    wheel_id = int(ide.get("wheel_id", 0))
    wheel_front = float(ide.get("wheel_scale_front", 0.7))
    wheel_rear = float(ide.get("wheel_scale_rear", 0.7))

    health = float((doc.get("damage") or {}).get("spawn_health", 1000.0))
    if health <= 0:
        raise VehicleError("damage.spawn_health must be > 0 (SASDK: <= 0 wrecks the car)")

    return {
        "name": name,
        "slug": slug,
        "author": str(meta.get("author") or ""),
        "notes": str(meta.get("notes") or ""),
        "model_id": model_id,
        "stock": stock,
        "keep_stock_filenames": keep_names,
        "handling_id": handling_id,
        "assets": assets,
        "handling": handling,
        "drive": drive,
        "engine": engine,
        "gears": gears,
        "percent": percent,
        "abs_flag": abs_flag,
        "anim": anim,
        "money": money,
        "model_flags": model_flags,
        "handling_flags": handling_flags,
        "front_lights": front_lights,
        "rear_lights": rear_lights,
        "dff_name": dff_name,
        "txd_name": txd_name,
        "veh_type": veh_type,
        "game_name": game_name,
        "anims": anims,
        "veh_class": veh_class,
        "frequency": frequency,
        "ide_flags": ide_flags,
        "comprules": comprules,
        "wheel_id": wheel_id,
        "wheel_front": wheel_front,
        "wheel_rear": wheel_rear,
        "spawn_health": health,
        "apply_mode": str(doc.get("samp", {}).get("apply_mode") or "model"),
    }


def fmt_f(value: Any) -> str:
    n = float(value)
    text = f"{n:.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return text


def handling_cfg_line(v: dict[str, Any]) -> str:
    h = v["handling"]
    com = f"{fmt_f(h['centre_of_mass_x'])} {fmt_f(h['centre_of_mass_y'])} {fmt_f(h['centre_of_mass_z'])}"
    cols = [
        v["handling_id"],
        fmt_f(h["mass"]),
        fmt_f(h["turn_mass"]),
        fmt_f(h["drag_multiplier"]),
        com,
        str(v["percent"]),
        fmt_f(h["traction_multiplier"]),
        fmt_f(h["traction_loss"]),
        fmt_f(h["traction_bias"]),
        str(v["gears"]),
        fmt_f(h["max_velocity"]),
        fmt_f(h["engine_acceleration"]),
        fmt_f(h["engine_inertia"]),
        v["drive"],
        v["engine"],
        fmt_f(h["brake_deceleration"]),
        fmt_f(h["brake_bias"]),
        str(v["abs_flag"]),
        fmt_f(h["steering_lock"]),
        fmt_f(h["suspension_force_level"]),
        fmt_f(h["suspension_damping_level"]),
        fmt_f(h["suspension_high_spd_com_damp"]),
        fmt_f(h["suspension_upper_limit"]),
        fmt_f(h["suspension_lower_limit"]),
        fmt_f(h["suspension_bias"]),
        fmt_f(h["suspension_anti_dive"]),
        fmt_f(h["seat_offset_distance"]),
        fmt_f(h["collision_damage_multiplier"]),
        str(v["money"]),
        f"{v['model_flags']:X}",
        f"{v['handling_flags']:X}",
        str(v["front_lights"]),
        str(v["rear_lights"]),
        str(v["anim"]),
    ]
    return "\t".join(cols) + "\n"


def vehicles_ide_line(v: dict[str, Any]) -> str:
    # id, dff, txd, type, handlingId, gameName, anims, class, freq, flags, comprules, wheelId, wheelScaleF, wheelScaleR
    return (
        f"{v['model_id']}, {v['dff_name']}, {v['txd_name']}, {v['veh_type']}, "
        f"{v['handling_id']}, {v['game_name']},\t{v['anims']},\t{v['veh_class']},\t"
        f"{v['frequency']},\t{v['ide_flags']},\t{v['comprules']},\t\t"
        f"{v['wheel_id']},\t{fmt_f(v['wheel_front'])},\t{fmt_f(v['wheel_rear'])}\n"
    )


def pawn_script(v: dict[str, Any]) -> str:
    mid = v["model_id"]
    h = v["handling"]
    setter = "SetModelHandlingFloat" if v["apply_mode"] != "vehicle" else "SetVehicleHandlingFloat"
    setter_i = "SetModelHandlingInt" if v["apply_mode"] != "vehicle" else "SetVehicleHandlingInt"
    target = "modelid" if v["apply_mode"] != "vehicle" else "vehicleid"
    extra = (
        f"ApplyCustomHandling_{v['slug'].replace('-', '_')}({mid});"
        if v["apply_mode"] != "vehicle"
        else "// Call ApplyCustomHandling_... (vehicleid) after CreateVehicle"
    )

    def fcall(attr: str, key: str) -> str:
        return f"\t{setter}({target}, {attr}, {fmt_f(h[key])});"

    def icall(attr: str, value: Any) -> str:
        return f"\t{setter_i}({target}, {attr}, {value});"

    drive_ord = ord(v["drive"])
    engine_ord = ord(v["engine"])
    fn = f"ApplyCustomHandling_{v['slug'].replace('-', '_')}"
    arg = "modelid" if v["apply_mode"] != "vehicle" else "vehicleid"
    body = "\n".join(
        [
            fcall("HANDL_FMASS", "mass"),
            fcall("HANDL_FTURNMASS", "turn_mass"),
            fcall("HANDL_FDRAGMULTIPLIER", "drag_multiplier"),
            fcall("HANDL_CENTREOFMASS_X", "centre_of_mass_x"),
            fcall("HANDL_CENTREOFMASS_Y", "centre_of_mass_y"),
            fcall("HANDL_CENTREOFMASS_Z", "centre_of_mass_z"),
            icall("HANDL_NPERCENTSUBMERGED", v["percent"]),
            fcall("HANDL_FTRACTIONMULTIPLIER", "traction_multiplier"),
            fcall("HANDL_FTRACTIONLOSS", "traction_loss"),
            fcall("HANDL_FTRACTIONBIAS", "traction_bias"),
            icall("HANDL_TR_NNUMBEROFGEARS", v["gears"]),
            fcall("HANDL_TR_FMAXVELOCITY", "max_velocity"),
            fcall("HANDL_TR_FENGINEACCELERATION", "engine_acceleration"),
            fcall("HANDL_TR_FENGINEINERTIA", "engine_inertia"),
            icall("HANDL_TR_NDRIVETYPE", drive_ord),
            icall("HANDL_TR_NENGINETYPE", engine_ord),
            fcall("HANDL_FBRAKEDECELERATION", "brake_deceleration"),
            fcall("HANDL_FBRAKEBIAS", "brake_bias"),
            icall("HANDL_BABS", v["abs_flag"]),
            fcall("HANDL_FSTEERINGLOCK", "steering_lock"),
            fcall("HANDL_FSUSPENSIONFORCELEVEL", "suspension_force_level"),
            fcall("HANDL_FSUSPENSIONDAMPINGLEVEL", "suspension_damping_level"),
            fcall("HANDL_FSUSPENSIONHIGHSPDCOMDAMP", "suspension_high_spd_com_damp"),
            fcall("HANDL_FSUSPENSIONUPPERLIMIT", "suspension_upper_limit"),
            fcall("HANDL_FSUSPENSIONLOWERLIMIT", "suspension_lower_limit"),
            fcall("HANDL_FSUSPENSIONBIAS", "suspension_bias"),
            fcall("HANDL_FSUSPENSIONANTIDIVEMULT", "suspension_anti_dive"),
            fcall("HANDL_FSEATOFFSETDISTANCE", "seat_offset_distance"),
            fcall("HANDL_FCOLLISIONDAMAGEMULT", "collision_damage_multiplier"),
            icall("HANDL_MODELFLAGS", v["model_flags"]),
            icall("HANDL_HANDLINGFLAGS", v["handling_flags"]),
            icall("HANDL_FRONTLIGHTS", v["front_lights"]),
            icall("HANDL_REARLIGHTS", v["rear_lights"]),
        ]
    )
    return f"""#define FILTERSCRIPT

#include <a_samp>
#include <chandlingsvr>

/*
 * Auto-generated by vehicle-generation/tools/generate_vehicle.py
 * Vehicle : {v['name']}
 * Replaces: model {mid} ({v['stock']['dff']})
 *
 * Players need matching DFF/TXD in GTA:SA (same filenames as the stock car
 * if keep_stock_filenames is true). Physics is pushed by CHandling.
 *
 * {extra}
 */

stock {fn}({arg})
{{
{body}
}}

public OnFilterScriptInit()
{{
#if !defined FILTERSCRIPT_NO_AUTO_APPLY
	{fn}({mid});
#endif
	printf("[vehicle-generation] applied '{v['name']}' handling to model {mid}");
	return 1;
}}

public OnVehicleSpawn(vehicleid)
{{
	if(GetVehicleModel(vehicleid) == {mid})
		SetVehicleHealth(vehicleid, {fmt_f(v['spawn_health'])});
	return 1;
}}
"""


def install_text(v: dict[str, Any], asset_notes: list[str]) -> str:
    stock_dff = v["stock"]["dff"]
    lines = [
        f"Vehicle: {v['name']}",
        f"Replace model ID: {v['model_id']} ({stock_dff})",
        f"handling.cfg identifier: {v['handling_id']}",
        "",
        "=== GTA:SA client files (every player must have these) ===",
        "",
        "1. Put your mesh/textures next to this folder, then copy them over the stock names:",
        f"     {stock_dff}.dff",
        f"     {stock_dff}.txd",
        "   Install with one of:",
        "     a) ModLoader:  GTA San Andreas/modloader/<your-mod>/" + f"{stock_dff}.dff and .txd",
        "     b) IMG Tool 2.0: replace entries inside models/gta3.img (backup first)",
        "     c) Fastman92 / 0.3.DL custom models (only if you are NOT using filename replace)",
        "",
        "2. Collision: COL is usually baked into the DFF. If you have a separate .col,",
        "   the COL model name (22 chars) must match the DFF name.",
        "",
        "3. Single-player / offline physics: replace the matching line in",
        "     GTA San Andreas/data/handling.cfg",
        f"   Look for identifier {v['handling_id']} and paste handling.cfg.line.txt over that line.",
        "   Backup handling.cfg first.",
        "",
        "4. vehicles.ide: ONLY edit data/vehicles.ide if keep_stock_filenames is false",
        "   or you changed wheel scale / vehicle class. For normal SA-MP replace mods,",
        "   leave vehicles.ide alone so streaming still finds infernus.dff etc.",
        "",
        "=== SA-MP server ===",
        "",
        "1. Copy ../../chandling-svr/chandlingsvr.inc into pawno/include/",
        "2. Put the compiled chandling plugin in server plugins/ and enable it in server.cfg",
        "3. Players need the matching client CHandling plugin (github.com/dotSILENT/chandling)",
        "4. Compile samp/chandling.pwn as a filterscript and add it to filterscripts in server.cfg",
        f"5. Spawn with CreateVehicle({v['model_id']}, x, y, z, angle, -1, -1, 0);",
        "",
        "SASDK note: live health is CVehicle::m_fHealth @ +0x4C0. Full = 1000. <= 0 wrecks.",
        "Collision damage uses handling.collision_damage_multiplier (0 = tank, ~1 = fragile).",
        "",
        "Asset checks:",
    ]
    lines.extend(f"  - {n}" for n in asset_notes)
    return "\n".join(lines) + "\n"


def inspect_rw(path: Path, expect: int, label: str) -> str:
    data = path.read_bytes()
    if len(data) < 12:
        return f"{label}: too small ({len(data)} bytes)"
    chunk_type, size, version = struct.unpack_from("<III", data, 0)
    ok = chunk_type == expect
    ver_hi = (version >> 16) & 0xFFFF
    return (
        f"{label}: {'OK' if ok else 'WRONG ROOT'} type=0x{chunk_type:04X} "
        f"payload={size} rw_version=0x{version:08X} (lib 0x{ver_hi:04X}) file={path.name}"
    )


def inspect_col(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 8:
        return f"COL: too small ({len(data)} bytes)"
    magic = data[0:4]
    if magic not in COL_MAGICS:
        return f"COL: unknown magic {magic!r} (want COLL/COL2/COL3)"
    name = data[8:30].split(b"\0", 1)[0].decode("ascii", errors="replace")
    model_id = struct.unpack_from("<H", data, 30)[0] if len(data) >= 32 else 0
    return f"COL: OK magic={magic.decode()} name='{name}' model_id={model_id}"


def check_assets(v: dict[str, Any], json_dir: Path) -> list[str]:
    notes: list[str] = []
    assets = v["assets"]
    mapping = [
        ("dff", RW_CLUMP, "DFF (RpClump)"),
        ("txd", RW_TEX_DICTIONARY, "TXD (RwTexDictionary)"),
    ]
    for key, expect, label in mapping:
        rel = assets.get(key)
        if not rel:
            notes.append(f"{label}: path not set in JSON (assets.{key})")
            continue
        path = (json_dir / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
        if not path.is_file():
            notes.append(f"{label}: missing file {path}")
            continue
        notes.append(inspect_rw(path, expect, label))
    col = assets.get("col")
    if col:
        path = (json_dir / col).resolve() if not Path(col).is_absolute() else Path(col)
        if not path.is_file():
            notes.append(f"COL: missing file {path}")
        else:
            notes.append(inspect_col(path))
    else:
        notes.append("COL: none listed (normal if collision is inside the DFF)")
    return notes


def write_outputs(v: dict[str, Any], json_path: Path, out_root: Path) -> Path:
    dest = out_root / v["slug"]
    dest.mkdir(parents=True, exist_ok=True)
    samp = dest / "samp"
    samp.mkdir(exist_ok=True)
    notes = check_assets(v, json_path.parent)
    (dest / "handling.cfg.line.txt").write_text(handling_cfg_line(v), encoding="utf-8")
    (dest / "vehicles.ide.line.txt").write_text(vehicles_ide_line(v), encoding="utf-8")
    (samp / "chandling.pwn").write_text(pawn_script(v), encoding="utf-8")
    (dest / "INSTALL.txt").write_text(install_text(v, notes), encoding="utf-8")
    snapshot = {
        "name": v["name"],
        "model_id": v["model_id"],
        "handling_id": v["handling_id"],
        "dff_name": v["dff_name"],
        "txd_name": v["txd_name"],
        "model_flags_hex": f"{v['model_flags']:X}",
        "handling_flags_hex": f"{v['handling_flags']:X}",
        "spawn_health": v["spawn_health"],
        "asset_notes": notes,
    }
    (dest / "validated.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build GTA:SA / SA-MP vehicle files from JSON")
    parser.add_argument("json_file", help="Path to a vehicle JSON definition")
    parser.add_argument(
        "-o",
        "--output",
        default=str(ROOT / "output"),
        help="Output directory (default: vehicle-generation/output)",
    )
    parser.add_argument("--validate-only", action="store_true", help="Validate and print, do not write")
    args = parser.parse_args(argv)

    json_path = Path(args.json_file).resolve()
    if not json_path.is_file():
        print(f"error: file not found: {json_path}", file=sys.stderr)
        return 1

    try:
        doc = json.loads(json_path.read_text(encoding="utf-8"))
        v = validate(doc, load_ids())
        notes = check_assets(v, json_path.parent)
        if args.validate_only:
            print(f"OK  {v['name']}  model {v['model_id']}  handling {v['handling_id']}")
            print(handling_cfg_line(v), end="")
            for n in notes:
                print(" ", n)
            return 0
        dest = write_outputs(v, json_path, Path(args.output))
        print(f"wrote {dest}")
        for n in notes:
            print(" ", n)
        return 0
    except (json.JSONDecodeError, VehicleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
