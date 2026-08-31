from typing import Callable, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
try:  # pragma: no cover - depends on whether the CUDA extension is installed
    from torchmcubes import marching_cubes as _torch_marching_cubes
except ImportError:  # Apple Silicon: no CUDA, no compiled extension
    _torch_marching_cubes = None

from skimage.measure import marching_cubes as _skimage_marching_cubes


def _marching_cubes_cpu(volume: "torch.Tensor", threshold: float):
    """scikit-image stand-in for torchmcubes.

    Two conventions have to be matched or the mesh comes out inside-out and
    open at the bottom:

    `gradient_direction="ascent"` — the caller feeds in `density - threshold`,
    so the *interior* is where the field is large. scikit-image assumes the
    opposite by default, and gets every triangle's winding backwards; the mesh
    then reports a negative volume and `contains` answers the inverse of the
    truth, which is exactly the query a voxeliser makes.

    The border of `-inf` — the isosurface is only closed where the field
    crosses the threshold, and a building fills most of the grid, so without a
    guaranteed-outside shell the surface runs off the edge and the mesh is left
    open along the bottom. Padding costs one cell and is subtracted back off
    the vertices, so nothing downstream sees the difference.
    """
    padded = np.pad(volume.cpu().numpy(), 1, mode="constant", constant_values=-1e4)
    verts, faces, _normals, _values = _skimage_marching_cubes(
        padded, level=threshold, gradient_direction="ascent"
    )
    return (
        torch.from_numpy(verts.copy() - 1.0).float(),
        torch.from_numpy(faces.copy()).long(),
    )


class IsosurfaceHelper(nn.Module):
    points_range: Tuple[float, float] = (0, 1)

    @property
    def grid_vertices(self) -> torch.FloatTensor:
        raise NotImplementedError


class MarchingCubeHelper(IsosurfaceHelper):
    def __init__(self, resolution: int) -> None:
        super().__init__()
        self.resolution = resolution
        # torchmcubes needs a compiled CUDA extension; scikit-image does the same
        # job in numpy and is the only option on Apple Silicon.
        self.returns_ij_order = _torch_marching_cubes is None
        self.mc_func: Callable = _torch_marching_cubes or _marching_cubes_cpu
        self._grid_vertices: Optional[torch.FloatTensor] = None

    @property
    def grid_vertices(self) -> torch.FloatTensor:
        if self._grid_vertices is None:
            # keep the vertices on CPU so that we can support very large resolution
            x, y, z = (
                torch.linspace(*self.points_range, self.resolution),
                torch.linspace(*self.points_range, self.resolution),
                torch.linspace(*self.points_range, self.resolution),
            )
            x, y, z = torch.meshgrid(x, y, z, indexing="ij")
            verts = torch.cat(
                [x.reshape(-1, 1), y.reshape(-1, 1), z.reshape(-1, 1)], dim=-1
            ).reshape(-1, 3)
            self._grid_vertices = verts
        return self._grid_vertices

    def forward(
        self,
        level: torch.FloatTensor,
    ) -> Tuple[torch.FloatTensor, torch.LongTensor]:
        level = -level.view(self.resolution, self.resolution, self.resolution)
        try:
            v_pos, t_pos_idx = self.mc_func(level.detach(), 0.0)
        except AttributeError:
            print("torchmcubes was not compiled with CUDA support, use CPU version instead.")
            v_pos, t_pos_idx = self.mc_func(level.detach().cpu(), 0.0)
        if not self.returns_ij_order:
            v_pos = v_pos[..., [2, 1, 0]]
        v_pos = v_pos / (self.resolution - 1.0)
        return v_pos.to(level.device), t_pos_idx.to(level.device)
