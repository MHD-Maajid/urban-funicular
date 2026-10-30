# Asset drop folder

Put finished RenderWare files here, then point `assets.dff` / `assets.txd` / `assets.col` in your JSON at them.

```
assets/
  infernus.dff     ← mesh (RpClump, chunk 0x001C)
  infernus.txd     ← textures (RwTexDictionary, chunk 0x0021)
  infernus.col     ← optional; usually already inside the DFF
```

## Names that SA-MP streaming expects

If `replace.keep_stock_filenames` is `true` (recommended), the files you install into GTA:SA **must** use the stock names for the ID you replace.

| You replace | Files the game loads |
|-------------|----------------------|
| 411 Infernus | `infernus.dff` + `infernus.txd` |
| 560 Sultan | `sultan.dff` + `sultan.txd` |
| 400 Landstalker | `landstal.dff` + `landstal.txd` |

See `data/vehicle-ids.json` for every ID 400–611.

The generator does **not** convert FBX/OBJ into DFF. Export DFF/TXD from a GTA tool (Kam's Max scripts, ZModeler, Blender RenderWare add-on). This folder only validates headers and emits install instructions.

## Rules that actually crash the game if ignored

1. DFF root chunk must be `0x001C` (Clump). TXD root must be `0x0021`.
2. Texture names inside the DFF materials must exist in the TXD.
3. The collision model name (22-byte ASCII in COL2, see `include/sasdk/col.hpp`) must match the DFF name.
4. Wheel dummy names (`wheel_lf_dummy`, `wheel_rf_dummy`, `wheel_lb_dummy`, `wheel_rb_dummy`) must exist or wheels spawn at the origin.
5. SA 1.0 US (sa10us) DFF/TXD only. VC/III files will not stream correctly.
6. Do not exceed a sane poly count; a 200k-tri car will hitch every player on spawn.

SASDK can inspect these files with `RwStream::read_root` and `ColArchive::parse` (`include/sasdk/rw.hpp`, `include/sasdk/col.hpp`). The Python generator already checks the 12-byte RenderWare header.
