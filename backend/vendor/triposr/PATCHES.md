# Local changes to TripoSR

Vendored from https://github.com/VAST-AI-Research/TripoSR (MIT). Two edits, both
so it runs without CUDA. Re-apply them if you re-clone.

## `tsr/models/isosurface.py` — marching cubes without `torchmcubes`

Upstream imports `torchmcubes`, a CUDA extension that cannot be built on Apple
Silicon. Replaced with `skimage.measure.marching_cubes`, which needs two
conventions matched or the mesh is wrong in ways nothing reports:

- `gradient_direction="ascent"`. The caller passes `density - threshold`, so the
  interior is where the field is *large*; scikit-image assumes the opposite by
  default and inverts every triangle's winding. The mesh then reports a negative
  volume and `contains` answers the inverse of the truth — which is exactly the
  query the voxeliser makes.
- A border of `-1e4` before the call, subtracted back off the vertices after. The
  isosurface only closes where the field crosses the threshold, and a building
  fills most of the grid, so without a guaranteed-outside shell the surface runs
  off the edge and the mesh is left open along the bottom.

`torchmcubes` is still used when it is importable, and the vertex re-ordering
upstream does for it is skipped for the scikit-image path, which already returns
vertices in array-axis order.

## `tsr/utils.py` — `rembg` made optional

Upstream imports `rembg` at module scope for `remove_background`. This project
segments with SegFormer (`app/services/segment.py`), which is better at
buildings than a general background remover, so `rembg` is never installed. The
import is now guarded and `remove_background` raises a clear error if called
without it. `resize_foreground`, which *is* used, has no such dependency.

## Removed from the checkout

`.git`, `figures/`, `examples/` and `gradio_app.py` — 63 MB of material none of
which is imported. `run.py` is kept for reference but is not used; the entry
point is `app/services/reconstruct.py`.
