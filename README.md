# Vehicle generation

JSON → GTA:SA `handling.cfg` + `vehicles.ide` line + SA-MP CHandling script.

This folder is a **content pipeline**, not a mesh exporter. You still model the car in a GTA tool (DFF + TXD). You edit **one JSON file** for mass, acceleration, braking, damage, flags, and which vanilla ID the car replaces. The generator writes every file the game and the server need.

It is built from this repository:

| Piece | Where it was taken from |
|-------|-------------------------|
| Handling struct + flags | `chandling-svr/src/HandlingStruct.h` |
| Valid ranges | `chandling-svr/src/HandlingEnum.cpp` |
| Pawn natives | `chandling-svr/chandlingsvr.inc` |
| Default Infernus / Sultan / Landstalker numbers | `chandling-svr/src/HandlingDefault.cpp` |
| DFF/TXD chunk IDs | `include/sasdk/rw.hpp` |
| COL2 header | `include/sasdk/col.hpp` |
| IDE name length (24 bytes) | `include/sasdk/ide.hpp` |
| Vehicle health 1000 / wreck at 0 | `include/sasdk/game/sa10us/vehicle.hpp` (`m_fHealth` @ `0x4C0`) |
| Handling array size 0xE0 | `include/sasdk/game/sa10us/sa10us_db.inl` (`CHandlingData`) |

## Hard limit you must accept

Vanilla GTA:SA and SA-MP **0.3.7** only have vehicle models **400–611**. You do **not** add a 612th car. You **replace** an existing one (Infernus 411, Sultan 560, …).

Every player must have the same DFF/TXD in their GTA:SA folder. Physics can stay in `handling.cfg` (single player) or be pushed by the **CHandling** server plugin (SA-MP, recommended — players will not share a custom `handling.cfg`).

Adding a brand-new ID requires extra client mods (0.3.DL custom models, Fastman92 limit adjuster). This pipeline does not do that.

```
JSON  ──►  generate_vehicle.py  ──►  output/<slug>/
                                      handling.cfg.line.txt     (paste into GTA)
                                      vehicles.ide.line.txt     (usually unused)
                                      samp/chandling.pwn        (server filterscript)
                                      INSTALL.txt
                                      validated.json
```

## 1. One-time setup

- Python 3.8+ on PATH (`python --version`).
- A GTA:SA **1.0 US** install (same target as SASDK sa10us).
- SA-MP server + [chandling-svr](https://github.com/dotSILENT/chandling-svr) plugin from this repo (`chandling-svr/`).
- Players: matching **client** CHandling plugin from [dotSILENT/chandling](https://github.com/dotSILENT/chandling).
- Optional: [ModLoader](https://github.com/thelink2012/modloader) so you never touch `gta3.img`.
- A DFF/TXD exporter (ZModeler, 3ds Max + Kam's scripts, or a Blender RenderWare add-on).

## 2. Create a car (checklist)

### A. Pick a victim ID

Open `data/vehicle-ids.json`. Choose a stock car **close in size** to your mesh.

Examples:

- Super car → `411` infernus
- Tuned sedan → `560` sultan
- SUV → `400` landstal

Do not replace a bike (`461`) with a four-wheel mesh. Wheel dummies and anim groups will be wrong.

### B. Export DFF + TXD

1. Export `something.dff` and `something.txd` from your modeller.
2. Rename them to the **stock** filenames (`infernus.dff`, `infernus.txd`, …).
3. Drop them in `vehicle-generation/assets/`.
4. Collision: leave it inside the DFF unless you know you need a separate COL2.

### C. Copy a JSON and edit physics

```text
copy templates\vehicle.template.json examples\mycar.json
```

Minimum fields you actually care about:

```json
"replace": { "model_id": 411, "keep_stock_filenames": true },
"handling": {
  "engine_acceleration": 13.5,
  "max_velocity": 250.0,
  "brake_deceleration": 12.5,
  "collision_damage_multiplier": 0.55
},
"damage": { "spawn_health": 1000.0 }
```

| JSON field | Effect in game |
|------------|----------------|
| `engine_acceleration` | How hard it pulls (Infernus stock = 12) |
| `max_velocity` | Top speed cap (Infernus stock = 240) |
| `engine_inertia` | Throttle lag; lower = snappier; **must not be 0** |
| `brake_deceleration` | Braking force (Infernus stock = 11) |
| `brake_bias` | 0 = rear, 1 = front, ~0.5 = even |
| `collision_damage_multiplier` | Body damage from hits. 0.2 = tank, 0.7 = sports car, 1.0+ = glass |
| `damage.spawn_health` | `SetVehicleHealth`. SASDK: 1000 = full, `<= 0` = wrecked |
| `mass` / `turn_mass` | Weight and rotation; copy from a similar stock car first |
| `drive_type` | `R` rear, `F` front, `4` all-wheel |
| `engine_type` | `P` petrol, `D` diesel, `E` electric (sound/behaviour) |

Keep the rest of `handling` copied from a stock example in `examples/` until the car drives, then tune one field at a time.

Full names, ranges, and flag lists: `schema/handling-fields.md`.

### D. Generate

From this folder:

```bat
python tools\generate_vehicle.py examples\nightfire_infernus.json
```

Or validate without writing:

```bat
python tools\generate_vehicle.py examples\nightfire_infernus.json --validate-only
```

Success prints `wrote vehicle-generation\output\<slug>` and any DFF/TXD header notes. Missing asset files are warnings, not fatal (you can generate physics before the mesh exists).

### E. Install into GTA:SA (every player)

**Meshes (required for a custom look):**

Preferred — ModLoader, no IMG edit:

```text
GTA San Andreas\modloader\nightfire\infernus.dff
GTA San Andreas\modloader\nightfire\infernus.txd
```

Otherwise replace those two names inside `models\gta3.img` with IMG Tool 2.0. **Backup the IMG first.**

**Physics in single player only:**

1. Backup `GTA San Andreas\data\handling.cfg`.
2. Find the line that starts with the handling identifier (`INFERNUS`, `SULTAN`, `LANDSTAL`, …).
3. Replace **that entire line** with the contents of `output/<slug>/handling.cfg.line.txt`.

Do **not** add a second `INFERNUS` line. Do **not** change `vehicles.ide` when `keep_stock_filenames` is true — streaming already looks up `infernus.dff`.

### F. Install into the SA-MP server

1. Build / copy `chandling-svr` into `plugins\` and add it to `server.cfg` (`plugins chandling` / `chandling.so`).
2. Copy `chandling-svr\chandlingsvr.inc` into `pawno\include\`.
3. Compile `output/<slug>/samp/chandling.pwn` as a filterscript. Add it to `filterscripts` in `server.cfg`.
4. Spawn the replaced ID:

```pawn
CreateVehicle(411, 0.0, 0.0, 3.0, 90.0, -1, -1, 0);
```

`apply_mode: "model"` (default) calls `SetModelHandlingFloat` / `SetModelHandlingInt` so **every** Infernus on the server uses the JSON physics. `"vehicle"` would apply per vehicle id instead.

Players without the client CHandling plugin will see the custom **mesh** (if they installed DFF/TXD) but **stock physics**.

`OnVehicleSpawn` in the generated script sets health from `damage.spawn_health`.

## 3. Folder map

```
vehicle-generation/
  README.md                 ← this file
  templates/vehicle.template.json
  examples/                 ← Nightfire, Sultan Sport, Landstalker Heavy
  schema/vehicle.schema.json
  schema/handling-fields.md
  data/vehicle-ids.json     ← 400–611 dff + handling names
  tools/generate_vehicle.py
  assets/                   ← drop DFF/TXD/COL here
  output/                   ← generated, safe to delete
```

## 4. `vehicles.ide` line (advanced)

`output/<slug>/vehicles.ide.line.txt` looks like:

```text
411, infernus, infernus, car, INFERNUS, INFERNUS,	null,	executive,	10,	0,	0,		0,	0.7,	0.7
```

Use this only if you change wheel scale, vehicle class, or (not recommended on 0.3.7) the DFF filename. Then replace the matching line in `data/vehicles.ide`. Wrong DFF names here make the car invisible.

## 5. Common failures

| Symptom | Cause |
|---------|--------|
| Invisible car | DFF name ≠ stock name, or TXD missing |
| Wheels in the middle of the chassis | Dummy names missing in the DFF |
| Game crash on spawn | III/VC DFF, broken COL name, or huge mesh |
| Custom look, stock speed | CHandling client plugin missing, or filterscript not loaded |
| Custom speed in SP, stock in SA-MP | You edited `handling.cfg` only; SA-MP clients ignore the server's GTA folder |
| Generator error `engine_inertia ... not 0` | Rockstar and CHandling reject 0 inertia |
| Generator error `number_of_gears must be 1-5` | Plugin limit (see `HandlingEnum.cpp`) |
| Car explodes from a tap | `collision_damage_multiplier` too high and/or health too low |
| Car never dies | multiplier near 0 and health far above 1000 |

## 6. SASDK (optional live check)

After the car is in the game, an ASI linked to `SASDK::sasdk` can read the live vehicle:

```cpp
#include <sasdk/sasdk.hpp>
using namespace sasdk::sa10us;
if (CVehicle* pv = Game::player_vehicle()) {
    CVehicleRef veh(pv);
    // model_index @ 0x22, health @ 0x4C0
}
```

See `examples/vehicle_health.cpp` in the repo root.

---

Workflow once this is set up: edit JSON → run the generator → copy DFF/TXD into ModLoader → compile the filterscript. Do not hand-edit `handling.cfg` columns; the generator owns that line.
