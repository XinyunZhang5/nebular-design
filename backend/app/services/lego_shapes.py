"""Measured LEGO shapes. GENERATED — do not edit by hand.

Regenerate with scripts/build_shape_library.py. Every field below was read out of
the official LDraw geometry or counted from Rebrickable's set inventories; none of
it was recalled. `slope_dir` in particular is the number that decides how a slope
has to be rotated, and it is the one thing about a part that cannot be worked out
from its name.

230 shapes, each appearing in at least 150 released sets.
"""

from typing import NamedTuple


class Shape(NamedTuple):
    part_num: str
    name: str
    family: str
    width: int  # studs along LDraw +X
    depth: int  # studs along LDraw +Z
    height: float  # LDU, studs excluded
    # Where the part's origin sits inside its own geometry. There is no single
    # convention in the library — a Brick 1x1 runs y -4..24 (origin on the top
    # face) and a Cheese Slope runs -15.6..0 (origin on the bottom) — so to seat
    # a part on a surface at world Y = s, put its origin at s - y_max.
    y_min: float
    y_max: float
    # Horizontal extents, for the same reason. 3040b spans z -30..+10: its
    # footprint centre is at -10, not 0. Assuming a part is centred on its origin
    # puts every slope one stud out of place, and never says so.
    x_min: float
    x_max: float
    z_min: float
    z_max: float
    has_studs: bool
    # Which horizontal axis the top surface descends along, and in which
    # direction, measured off the vertices. None for a flat-topped part.
    slope_axis: str | None
    slope_dir: str | None
    slope_drop: float
    sets: int  # set inventories this part appears in


SHAPES: list[Shape] = [
    Shape('3659', 'Brick Arch 1 x 4', 'arch', 4, 1, 24.0, -4.0, 24.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 1236),
    Shape('92950', 'Brick Arch 1 x 6 Raised Arch', 'arch', 6, 1, 24.0, -4.0, 24.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 715),
    Shape('6005', 'Brick Arch 1 x 3 x 2 Curved Top', 'arch', 1, 3, 48.0, 0.0, 48.0, -10.0, 10.0, -50.0, 10.0, False, 'z', '-', 7.7, 487),
    Shape('88292', 'Brick Arch 1 x 3 x 2', 'arch', 1, 3, 48.0, -4.0, 48.0, -10.0, 10.0, -10.0, 50.0, True, 'z', '-', 20.0, 457),
    Shape('13965', 'Brick Arch 1 x 3 x 3 [Gothic]', 'arch', 1, 3, 72.0, -4.0, 72.0, -10.0, 10.0, -10.0, 50.0, True, 'z', '-', 20.0, 445),
    Shape('15254', 'Brick Arch 1 x 6 x 2 - Thin Top without Reinforced Underside [New Version]', 'arch', 6, 1, 48.0, -4.0, 48.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 440),
    Shape('4490', 'Brick Arch 1 x 3', 'arch', 3, 1, 24.0, -4.0, 24.0, -30.0, 30.0, -10.0, 10.0, True, None, None, 0.0, 416),
    Shape('6182', 'Brick Arch 1 x 4 x 2', 'arch', 4, 1, 48.0, -4.0, 48.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 378),
    Shape('14395', 'Brick Arch 1 x 5 x 4 [Continuous Bow, Raised Underside Cross Supports]', 'arch', 1, 5, 96.0, -4.0, 96.0, -10.0, 10.0, -10.0, 90.0, True, 'z', '-', 16.0, 305),
    Shape('16577', 'Brick Arch 1 x 8 x 2 Raised', 'arch', 8, 1, 48.0, -4.0, 48.0, -80.0, 80.0, -10.0, 10.0, True, None, None, 0.0, 304),
    Shape('3455', 'Brick Arch 1 x 6', 'arch', 6, 1, 24.0, -4.0, 24.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 286),
    Shape('3307', 'Brick Arch 1 x 6 x 2 - Thick Top with Reinforced Underside', 'arch', 6, 1, 48.0, -4.0, 48.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 263),
    Shape('3308', 'Brick Arch 1 x 8 x 2', 'arch', 8, 1, 48.0, -4.0, 48.0, -80.0, 80.0, -10.0, 10.0, True, None, None, 0.0, 238),
    Shape('2339', 'Brick Arch 1 x 5 x 4 [Continuous Bow]', 'arch', 1, 5, 96.0, -4.0, 96.0, -10.0, 10.0, -10.0, 90.0, True, 'z', '-', 16.0, 187),
    Shape('6060', 'Brick Arch 1 x 6 x 3 1/3 Curved Top', 'arch', 1, 6, 80.0, 0.0, 80.0, -10.0, 10.0, -100.0, 20.0, False, 'z', '-', 19.4, 158),
    Shape('6183', 'Brick Arch 1 x 6 x 2 Curved Top', 'arch', 6, 1, 48.0, -4.0, 48.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 156),
    Shape('3004', 'Brick 1 x 2', 'brick', 2, 1, 24.0, -4.0, 24.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 7455),
    Shape('3005', 'Brick 1 x 1', 'brick', 1, 1, 24.0, -4.0, 24.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 5689),
    Shape('3010', 'Brick 1 x 4', 'brick', 4, 1, 24.0, -4.0, 24.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 5499),
    Shape('3003', 'Brick 2 x 2', 'brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 5042),
    Shape('3001', 'Brick 2 x 4', 'brick', 4, 2, 24.0, -4.0, 24.0, -40.0, 40.0, -20.0, 20.0, True, None, None, 0.0, 4632),
    Shape('3009', 'Brick 1 x 6', 'brick', 6, 1, 24.0, -4.0, 24.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 3832),
    Shape('3622', 'Brick 1 x 3', 'brick', 3, 1, 24.0, -4.0, 24.0, -30.0, 30.0, -10.0, 10.0, True, None, None, 0.0, 3566),
    Shape('3002', 'Brick 2 x 3', 'brick', 3, 2, 24.0, -4.0, 24.0, -30.0, 30.0, -20.0, 20.0, True, None, None, 0.0, 3009),
    Shape('3008', 'Brick 1 x 8', 'brick', 8, 1, 24.0, -4.0, 24.0, -80.0, 80.0, -10.0, 10.0, True, None, None, 0.0, 2420),
    Shape('2456', 'Brick 2 x 6', 'brick', 6, 2, 24.0, -4.0, 24.0, -60.0, 60.0, -20.0, 20.0, True, None, None, 0.0, 2168),
    Shape('3007', 'Brick 2 x 8', 'brick', 8, 2, 24.0, -4.0, 24.0, -80.0, 80.0, -20.0, 20.0, True, None, None, 0.0, 1413),
    Shape('6111', 'Brick 1 x 10', 'brick', 10, 1, 24.0, -4.0, 24.0, -100.0, 100.0, -10.0, 10.0, True, None, None, 0.0, 997),
    Shape('6112', 'Brick 1 x 12', 'brick', 12, 1, 24.0, -4.0, 24.0, -120.0, 120.0, -10.0, 10.0, True, None, None, 0.0, 855),
    Shape('3006', 'Brick 2 x 10', 'brick', 10, 2, 24.0, -4.0, 24.0, -100.0, 100.0, -20.0, 20.0, True, None, None, 0.0, 781),
    Shape('2465', 'Brick 1 x 16', 'brick', 16, 1, 24.0, -4.0, 24.0, -160.0, 160.0, -10.0, 10.0, True, None, None, 0.0, 747),
    Shape('59900', 'Cone 1 x 1 [Top Groove]', 'cone', 1, 1, 24.0, -4.0, 24.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 3415),
    Shape('4589', 'Cone 1 x 1 [No Top Groove]', 'cone', 1, 1, 24.0, -4.0, 24.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 1092),
    Shape('3942c', 'Cone 2 x 2 x 2, Open Stud', 'cone', 2, 2, 48.0, -4.0, 48.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 812),
    Shape('6233', 'Cone 3 x 3 x 2', 'cone', 3, 3, 48.0, -4.0, 48.0, -30.0, 30.0, -30.0, 30.0, True, None, None, 0.0, 214),
    Shape('3943b', 'Cone 4 x 4 x 2, Axle Hole [Plain]', 'cone', 4, 4, 48.0, -4.0, 48.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 211),
    Shape('11477', 'Brick Curved 2 x 1 No Studs [1/2 Bow]', 'curved', 1, 2, 16.0, -16.0, 0.0, -10.0, 10.0, -20.0, 20.0, False, 'z', '-', 8.5, 3514),
    Shape('15068', 'Brick Curved 2 x 2 x 2/3', 'curved', 2, 2, 16.0, -16.0, 0.0, -20.0, 20.0, -20.0, 20.0, False, 'z', '-', 8.5, 3134),
    Shape('6091', 'Brick Curved 1 x 2 x 1 1/3 with Curved Top', 'curved', 1, 2, 32.0, 0.0, 32.0, -10.0, 10.0, -30.0, 10.0, False, None, None, 0.0, 2239),
    Shape('93273', 'Brick Curved 4 x 1 Double with No Studs', 'curved', 1, 4, 16.0, -16.0, 0.0, -10.0, 10.0, -40.0, 40.0, False, None, None, 0.0, 2049),
    Shape('50950', 'Brick Curved 3 x 1 No Studs', 'curved', 1, 3, 24.0, 0.0, 24.0, -10.0, 10.0, -30.0, 30.0, False, 'z', '-', 14.1, 1880),
    Shape('47457', 'Brick Curved 2 x 2 x 2/3 Two Studs and Curved Slope End', 'curved', 2, 2, 16.0, -4.0, 16.0, -20.0, 20.0, -30.0, 10.0, True, None, None, 0.0, 1155),
    Shape('11153', 'Brick Curved 4 x 1 No Studs [Stud Holder with Symmetric Ridges]', 'curved', 1, 4, 24.0, 0.0, 24.0, -10.0, 10.0, -40.0, 40.0, False, 'z', '-', 11.4, 1069),
    Shape('37352', 'Brick Curved 1 x 2 x 1 No Studs', 'curved', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, 'z', '-', 11.0, 937),
    Shape('49307', 'Brick Curved 1 x 1 x 2/3 Double Curved Top, No Studs', 'curved', 1, 1, 16.0, -16.0, 0.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 897),
    Shape('93606', 'Brick Curved 4 x 2 No Studs', 'curved', 2, 4, 24.0, 0.0, 24.0, -20.0, 20.0, -40.0, 40.0, False, 'z', '-', 11.4, 698),
    Shape('88930', 'Brick Curved 2 x 4 x 2/3 No Studs, with Bottom Tubes', 'curved', 4, 2, 16.0, -16.0, 0.0, -40.0, 40.0, -20.0, 20.0, False, 'z', '-', 8.5, 618),
    Shape('30165', 'Brick Curved 2 x 2, Two Top Studs', 'curved', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 516),
    Shape('42022', 'Brick Curved 6 x 1', 'curved', 1, 6, 24.0, -4.0, 24.0, -10.0, 10.0, -100.0, 20.0, True, 'z', '-', 12.0, 496),
    Shape('18653', 'Brick Curved 1 x 3 x 2 Inverted [Inside Bow]', 'curved', 3, 1, 48.0, -4.0, 48.0, -10.0, 50.0, -10.0, 10.0, True, 'x', '+', 38.6, 483),
    Shape('6215', 'Brick Curved 2 x 3', 'curved', 3, 2, 24.0, -4.0, 24.0, -20.0, 40.0, -20.0, 20.0, True, None, None, 0.0, 467),
    Shape('24309', 'Brick Curved 3 x 2 No Studs', 'curved', 2, 3, 24.0, 0.0, 24.0, -20.0, 20.0, -30.0, 30.0, False, 'z', '-', 14.1, 454),
    Shape('78666', 'Brick Curved 2 x 1 with Inverted Cutout', 'curved', 2, 1, 24.0, -4.0, 24.0, -10.0, 30.0, -10.0, 10.0, True, 'x', '+', 14.5, 386),
    Shape('6081', 'Brick Curved 2 x 4 x 1 1/3', 'curved', 4, 2, 32.0, 0.0, 32.0, -40.0, 40.0, -30.0, 10.0, False, None, None, 0.0, 368),
    Shape('13731', 'Brick Curved 10 x 1 [Symmetric Inside Ridges]', 'curved', 1, 10, 24.0, -8.0, 16.0, -10.0, 10.0, -180.0, 20.0, False, 'z', '-', 10.8, 301),
    Shape('5841', 'Brick Curved 1 x 2 x 1 with Curved Top', 'curved', 1, 2, 24.0, 0.0, 24.0, -10.0, 10.0, -30.0, 10.0, False, None, None, 0.0, 256),
    Shape('10314', 'Brick Curved 1 x 4 x 1 1/3 No Studs', 'curved', 4, 1, 32.0, 0.0, 32.0, -40.0, 40.0, -10.0, 10.0, False, 'z', '-', 12.3, 246),
    Shape('61678', 'Brick Curved 4 x 1 No Studs [Stud Holder with Asymmetric Ridges]', 'curved', 1, 4, 24.0, 0.0, 24.0, -10.0, 10.0, -40.0, 40.0, False, 'z', '-', 11.4, 231),
    Shape('30099', 'Brick Curved 1 x 5 x 4 Inverted', 'curved', 5, 1, 96.0, -4.0, 96.0, -10.0, 90.0, -10.0, 10.0, True, 'x', '+', 77.3, 228),
    Shape('44126', 'Brick Curved 6 x 2', 'curved', 2, 6, 24.0, -4.0, 24.0, -20.0, 20.0, -100.0, 20.0, True, 'z', '-', 12.0, 226),
    Shape('79756', 'Brick Curved 1 x 4 x 2/3 Double, No Studs', 'curved', 4, 1, 16.0, -16.0, 0.0, -40.0, 40.0, -10.0, 10.0, False, None, None, 0.0, 201),
    Shape('33243', 'Brick Curved 1 x 3 x 2', 'curved', 1, 3, 48.0, -4.0, 48.0, -10.0, 10.0, -50.0, 10.0, True, 'z', '-', 11.7, 197),
    Shape('4740', 'Dish 2 x 2 Inverted [Radar]', 'dish', 2, 2, 8.0, -4.0, 8.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 2680),
    Shape('43898', 'Dish 3 x 3 Inverted [Radar]', 'dish', 3, 3, 16.0, -4.0, 16.0, -30.0, 30.0, -30.0, 30.0, True, None, None, 0.0, 856),
    Shape('3960', 'Dish 4 x 4 Inverted [Radar]', 'dish', 4, 4, 16.0, -4.0, 16.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 646),
    Shape('44375b', 'Dish 6 x 6 Inverted (Radar) with Solid Studs', 'dish', 6, 6, 16.0, -4.0, 16.0, -60.0, 60.0, -60.0, 60.0, True, None, None, 0.0, 234),
    Shape('4285b', 'Dish 6 x 6 Inverted, Radar / Webbed [Anti-studs at 90°]', 'dish', 6, 6, 16.0, -4.0, 16.0, -60.0, 60.0, -60.0, 60.0, True, None, None, 0.0, 180),
    Shape('4865b', 'Panel 1 x 2 x 1 [Rounded Corners]', 'panel', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, 'z', '-', 16.0, 1439),
    Shape('4865a', 'Panel 1 x 2 x 1 [Square Corners]', 'panel', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, 'z', '-', 16.0, 1010),
    Shape('6231', 'Panel 1 x 1 x 1 Corner', 'panel', 1, 1, 24.0, 0.0, 24.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 911),
    Shape('87552', 'Panel 1 x 2 x 2 [Side Supports / Hollow Studs]', 'panel', 2, 1, 48.0, -4.0, 48.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 849),
    Shape('15207', 'Panel 1 x 4 x 1 with Rounded Corners [Thin Wall]', 'panel', 4, 1, 24.0, 0.0, 24.0, -40.0, 40.0, -10.0, 10.0, False, 'z', '-', 16.0, 783),
    Shape('60581', 'Panel 1 x 4 x 3 [Side Supports / Hollow Studs]', 'panel', 4, 1, 72.0, -4.0, 72.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 685),
    Shape('23969', 'Panel 1 x 2 x 1 with Rounded Corners and 2 Sides', 'panel', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 675),
    Shape('87544', 'Panel 1 x 2 x 3 [Side Supports / Hollow Studs]', 'panel', 2, 1, 72.0, -4.0, 72.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 632),
    Shape('59349', 'Panel 1 x 6 x 5', 'panel', 6, 1, 120.0, -4.0, 120.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 568),
    Shape('93095', 'Panel 1 x 2 x 1 with Rounded Corners and Central Divider', 'panel', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 494),
    Shape('14718', 'Panel 1 x 4 x 2 with Side Supports - Hollow Studs', 'panel', 4, 1, 48.0, -4.0, 48.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 312),
    Shape('43337', 'Panel 1 x 4 x 1 with Rounded Corners [Thick Wall]', 'panel', 4, 1, 24.0, 0.0, 24.0, -40.0, 40.0, -10.0, 10.0, False, 'z', '-', 16.0, 311),
    Shape('23950', 'Panel 1 x 3 x 1', 'panel', 3, 1, 24.0, 0.0, 24.0, -30.0, 30.0, -10.0, 10.0, False, 'z', '-', 16.0, 239),
    Shape('4864b', 'Panel 1 x 2 x 2 [Hollow Studs]', 'panel', 2, 1, 48.0, -4.0, 48.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 192),
    Shape('4215b', 'Panel 1 x 4 x 3 [Hollow Studs]', 'panel', 4, 1, 72.0, -4.0, 72.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 189),
    Shape('30562', 'Panel 4 x 4 x 6 Quarter Cylinder', 'panel', 4, 4, 144.0, -4.0, 144.0, 0.0, 80.0, -80.0, 0.0, True, None, None, 0.0, 181),
    Shape('91501', 'Panel 2 x 2 x 1 Corner', 'panel', 2, 2, 24.0, 0.0, 24.0, -10.0, 30.0, -30.0, 10.0, False, None, None, 0.0, 156),
    Shape('3023', 'Plate 1 x 2', 'plate', 2, 1, 8.0, -4.0, 8.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 10074),
    Shape('3020', 'Plate 2 x 4', 'plate', 4, 2, 8.0, -4.0, 8.0, -40.0, 40.0, -20.0, 20.0, True, None, None, 0.0, 8607),
    Shape('3022', 'Plate 2 x 2', 'plate', 2, 2, 8.0, -4.0, 8.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 8523),
    Shape('3710', 'Plate 1 x 4', 'plate', 4, 1, 8.0, -4.0, 8.0, -40.0, 40.0, -10.0, 10.0, True, None, None, 0.0, 7726),
    Shape('3021', 'Plate 2 x 3', 'plate', 3, 2, 8.0, -4.0, 8.0, -30.0, 30.0, -20.0, 20.0, True, None, None, 0.0, 7144),
    Shape('3795', 'Plate 2 x 6', 'plate', 6, 2, 8.0, -4.0, 8.0, -60.0, 60.0, -20.0, 20.0, True, None, None, 0.0, 6242),
    Shape('3024', 'Plate 1 x 1', 'plate', 1, 1, 8.0, -4.0, 8.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 6142),
    Shape('3666', 'Plate 1 x 6', 'plate', 6, 1, 8.0, -4.0, 8.0, -60.0, 60.0, -10.0, 10.0, True, None, None, 0.0, 5609),
    Shape('3623', 'Plate 1 x 3', 'plate', 3, 1, 8.0, -4.0, 8.0, -30.0, 30.0, -10.0, 10.0, True, None, None, 0.0, 5163),
    Shape('3034', 'Plate 2 x 8', 'plate', 8, 2, 8.0, -4.0, 8.0, -80.0, 80.0, -20.0, 20.0, True, None, None, 0.0, 4551),
    Shape('3460', 'Plate 1 x 8', 'plate', 8, 1, 8.0, -4.0, 8.0, -80.0, 80.0, -10.0, 10.0, True, None, None, 0.0, 3898),
    Shape('3031', 'Plate 4 x 4', 'plate', 4, 4, 8.0, -4.0, 8.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 3897),
    Shape('3032', 'Plate 4 x 6', 'plate', 6, 4, 8.0, -4.0, 8.0, -60.0, 60.0, -40.0, 40.0, True, None, None, 0.0, 3453),
    Shape('3832', 'Plate 2 x 10', 'plate', 10, 2, 8.0, -4.0, 8.0, -100.0, 100.0, -20.0, 20.0, True, None, None, 0.0, 2632),
    Shape('3035', 'Plate 4 x 8', 'plate', 8, 4, 8.0, -4.0, 8.0, -80.0, 80.0, -40.0, 40.0, True, None, None, 0.0, 2581),
    Shape('4477', 'Plate 1 x 10', 'plate', 10, 1, 8.0, -4.0, 8.0, -100.0, 100.0, -10.0, 10.0, True, None, None, 0.0, 2374),
    Shape('3036', 'Plate 6 x 8', 'plate', 8, 6, 8.0, -4.0, 8.0, -80.0, 80.0, -60.0, 60.0, True, None, None, 0.0, 1864),
    Shape('2445', 'Plate 2 x 12', 'plate', 12, 2, 8.0, -4.0, 8.0, -120.0, 120.0, -20.0, 20.0, True, None, None, 0.0, 1825),
    Shape('3958', 'Plate 6 x 6', 'plate', 6, 6, 8.0, -4.0, 8.0, -60.0, 60.0, -60.0, 60.0, True, None, None, 0.0, 1803),
    Shape('3030', 'Plate 4 x 10', 'plate', 10, 4, 8.0, -4.0, 8.0, -100.0, 100.0, -40.0, 40.0, True, None, None, 0.0, 1448),
    Shape('4282', 'Plate 2 x 16', 'plate', 16, 2, 8.0, -4.0, 8.0, -160.0, 160.0, -20.0, 20.0, True, None, None, 0.0, 1274),
    Shape('3033', 'Plate 6 x 10', 'plate', 10, 6, 8.0, -4.0, 8.0, -100.0, 100.0, -60.0, 60.0, True, None, None, 0.0, 1257),
    Shape('3029', 'Plate 4 x 12', 'plate', 12, 4, 8.0, -4.0, 8.0, -120.0, 120.0, -40.0, 40.0, True, None, None, 0.0, 1175),
    Shape('60479', 'Plate 1 x 12', 'plate', 12, 1, 8.0, -4.0, 8.0, -120.0, 120.0, -10.0, 10.0, True, None, None, 0.0, 1163),
    Shape('11212', 'Plate 3 x 3', 'plate', 3, 3, 8.0, -4.0, 8.0, -30.0, 30.0, -30.0, 30.0, True, None, None, 0.0, 1066),
    Shape('3028', 'Plate 6 x 12', 'plate', 12, 6, 8.0, -4.0, 8.0, -120.0, 120.0, -60.0, 60.0, True, None, None, 0.0, 860),
    Shape('41539', 'Plate 8 x 8', 'plate', 8, 8, 8.0, -4.0, 8.0, -80.0, 80.0, -80.0, 80.0, True, None, None, 0.0, 705),
    Shape('91988', 'Plate 2 x 14', 'plate', 14, 2, 8.0, -4.0, 8.0, -140.0, 140.0, -20.0, 20.0, True, None, None, 0.0, 675),
    Shape('78329', 'Plate 1 x 5', 'plate', 5, 1, 8.0, -4.0, 8.0, -50.0, 50.0, -10.0, 10.0, True, None, None, 0.0, 668),
    Shape('92438', 'Plate 8 x 16', 'plate', 16, 8, 8.0, -4.0, 8.0, -160.0, 160.0, -80.0, 80.0, True, None, None, 0.0, 605),
    Shape('3027', 'Plate 6 x 16', 'plate', 16, 6, 8.0, -4.0, 8.0, -160.0, 160.0, -60.0, 60.0, True, None, None, 0.0, 534),
    Shape('91405', 'Plate 16 x 16', 'plate', 16, 16, 8.0, -4.0, 8.0, -160.0, 160.0, -160.0, 160.0, True, None, None, 0.0, 348),
    Shape('3456', 'Plate 6 x 14', 'plate', 14, 6, 8.0, -4.0, 8.0, -140.0, 140.0, -60.0, 60.0, True, None, None, 0.0, 306),
    Shape('3062b', 'Brick Round 1 x 1 Open Stud', 'round_brick', 1, 1, 24.0, -4.0, 24.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 4942),
    Shape('92947', 'Brick Round 2 x 2 [Grill]', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 777),
    Shape('30367c', 'Brick Round 2 x 2 Dome Top, Hollow Stud', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 653),
    Shape('15395', 'Brick Round 2 x 2 Dome Bottom [Open Stud]', 'round_brick', 2, 2, 28.0, -20.0, 8.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 560),
    Shape('98100', 'Brick Round 2 x 2 Truncated Cone', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 517),
    Shape('87081', 'Brick Round 4 x 4 Centre Hole', 'round_brick', 4, 4, 24.0, -4.0, 24.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 496),
    Shape('25214', 'Brick Round 1 x 1 diameter Tube with 90 Degree Elbow (2 x 2 x 1) and Axle Holes (Crossholes) at each end', 'round_brick', 2, 2, 20.0, -10.0, 10.0, -30.0, 10.0, -10.0, 30.0, False, None, None, 0.0, 396),
    Shape('17485', 'Brick Round 2 x 2, Pin Holes', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 357),
    Shape('3062a', 'Brick Round 1 x 1 Solid Stud', 'round_brick', 1, 1, 24.0, -4.0, 24.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 320),
    Shape('30367b', 'Brick Round 2 x 2 Dome Top, Blocked Open Stud, Bottom Axle Holder', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 311),
    Shape('4588', 'Brick Round 1 x 1 with Fins, Open Stud', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 260),
    Shape('6222', 'Brick Round 4 x 4 with 4 Side Pin Holes and Center Axle Hole', 'round_brick', 4, 4, 24.0, -4.0, 24.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 256),
    Shape('3262', 'Brick Round 2 x 2 Dome Top, Vented Stud', 'round_brick', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 214),
    Shape('30151b', 'Brick Round 2 x 2 x 1 2/3 Dome Top, Hollow Stud', 'round_brick', 2, 2, 40.0, -4.0, 40.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 201),
    Shape('6141', 'Plate Round 1 x 1 with Solid Stud', 'round_plate', 1, 1, 8.0, -4.0, 8.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 8323),
    Shape('85861', 'Plate Round 1 x 1 with Open Stud', 'round_plate', 1, 1, 8.0, -4.0, 8.0, -10.0, 10.0, -10.0, 10.0, True, None, None, 0.0, 2694),
    Shape('11833', 'Plate Round 4 x 4 with 2 x 2 Round Opening', 'round_plate', 4, 4, 8.0, -4.0, 8.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 431),
    Shape('1745', 'Plate Round 1 x 2 Half Circle with Stud (Jumper)', 'round_plate', 2, 1, 8.0, -4.0, 8.0, -20.0, 20.0, -10.0, 10.0, True, None, None, 0.0, 361),
    Shape('15470', 'Plate Round 1 x 1 Swirled Top', 'round_plate', 1, 1, 18.0, -18.0, 0.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 359),
    Shape('53119', 'Plate Round 1 x 1 Swirled Top / Poo', 'round_plate', 1, 1, 20.0, -12.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 240),
    Shape('98138', 'Tile Round 1 x 1', 'round_tile', 1, 1, 8.0, 0.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 3775),
    Shape('25269', 'Tile Round 1 x 1 Quarter', 'round_tile', 1, 1, 8.0, 0.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 2073),
    Shape('20482', 'Tile Round 1 x 1 with Hollow Bar', 'round_tile', 1, 1, 16.0, -8.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 2022),
    Shape('14769', 'Tile Round 2 x 2 with Bottom Stud Holder', 'round_tile', 2, 2, 8.0, 0.0, 8.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 1810),
    Shape('24246', 'Tile Round 1 x 1 Half Circle', 'round_tile', 1, 1, 8.0, 0.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 1152),
    Shape('4150', 'Tile Round 2 x 2 with Bottom Cross', 'round_tile', 2, 2, 8.0, 0.0, 8.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 586),
    Shape('1748', 'Tile Round 1 x 2 Half Circle', 'round_tile', 2, 1, 8.0, 0.0, 8.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 556),
    Shape('67095', 'Tile Round 3 x 3', 'round_tile', 3, 3, 8.0, 0.0, 8.0, -30.0, 30.0, -30.0, 30.0, False, None, None, 0.0, 260),
    Shape('66857', 'Tile Round 2 x 4', 'round_tile', 2, 4, 8.0, 0.0, 8.0, -20.0, 20.0, -40.0, 40.0, False, None, None, 0.0, 244),
    Shape('1126', 'Tile Round 1 x 2', 'round_tile', 2, 1, 8.0, 0.0, 8.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 239),
    Shape('54200', 'Brick Sloped 30° 1 x 1 x 2/3 (Cheese Slope)', 'slope', 1, 1, 15.6, -15.6, 0.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 5565),
    Shape('3040b', 'Brick Sloped 45° 2 x 1 with Bottom Pin', 'slope', 1, 2, 24.0, -4.0, 24.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '-', 20.0, 4107),
    Shape('3039', 'Brick Sloped 45° 2 x 2', 'slope', 2, 2, 24.0, -4.0, 24.0, -20.0, 20.0, -30.0, 10.0, True, 'z', '-', 20.0, 3943),
    Shape('85984', 'Brick Sloped 30° 1 x 2 x 2/3', 'slope', 2, 1, 15.6, -15.6, 0.0, -20.0, 20.0, -10.0, 10.0, False, 'z', '-', 11.6, 3790),
    Shape('4286', 'Brick Sloped 33° 3 x 1', 'slope', 1, 3, 24.0, -4.0, 24.0, -10.0, 10.0, -50.0, 10.0, True, 'z', '-', 20.0, 2175),
    Shape('3298', 'Brick Sloped 33° 3 x 2', 'slope', 2, 3, 24.0, -4.0, 24.0, -20.0, 20.0, -50.0, 10.0, True, 'z', '-', 16.8, 1737),
    Shape('61409', 'Brick Sloped 18° 2 x 1 x 2/3 with 4 Slots / Grate', 'slope', 1, 2, 15.5, -15.5, 0.0, -10.0, 10.0, -20.0, 20.0, False, 'z', '-', 9.7, 1477),
    Shape('3037', 'Brick Sloped 45° 2 x 4', 'slope', 4, 2, 24.0, -4.0, 24.0, -40.0, 40.0, -30.0, 10.0, True, 'z', '-', 20.0, 1469),
    Shape('15672', 'Brick Sloped 45° 2 x 1 with 2/3 Cutout [New Version]', 'slope', 1, 2, 24.0, -16.0, 8.0, -10.0, 10.0, -20.0, 20.0, False, 'z', '-', 8.0, 1406),
    Shape('28192', 'Brick Sloped 45° 2 x 1 with 2/3 Inverted Cutout and no stud', 'slope', 1, 2, 24.0, 0.0, 24.0, -10.0, 10.0, -30.0, 10.0, False, 'z', '-', 20.0, 1044),
    Shape('60481', 'Brick Sloped 65° 2 x 1 x 2', 'slope', 1, 2, 48.0, -4.0, 48.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '-', 44.0, 1032),
    Shape('4460b', 'Brick Sloped 75° 2 x 1 x 3 with Hollow Stud', 'slope', 1, 2, 72.0, -4.0, 72.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '-', 67.0, 833),
    Shape('3678b', 'Brick Sloped 65° 2 x 2 x 2 with Bottom Tube', 'slope', 2, 2, 48.0, -4.0, 48.0, -20.0, 20.0, -30.0, 10.0, True, 'z', '-', 44.0, 780),
    Shape('3045', 'Brick Sloped 45° 2 x 2 Double Convex', 'slope', 2, 2, 24.0, -4.0, 24.0, -10.0, 30.0, -30.0, 10.0, True, 'x', '+', 20.0, 696),
    Shape('60477', 'Brick Sloped 18° 4 x 1', 'slope', 1, 4, 24.0, -4.0, 24.0, -10.0, 10.0, -70.0, 10.0, True, 'z', '-', 17.3, 645),
    Shape('3297', 'Brick Sloped 33° 3 x 4', 'slope', 4, 3, 24.0, -4.0, 24.0, -40.0, 40.0, -50.0, 10.0, True, 'z', '-', 16.8, 640),
    Shape('15571', 'Brick Sloped 45° 2 x 1 Triple with Inside Stud Holder', 'slope', 2, 1, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 622),
    Shape('30363', 'Brick Sloped 18° 4 x 2', 'slope', 2, 4, 24.0, -4.0, 24.0, -20.0, 20.0, -70.0, 10.0, True, 'z', '-', 17.3, 591),
    Shape('22388', 'Brick Sloped 45° 1 x 1 x 2/3 Quadruple Convex [Pyramid]', 'slope', 1, 1, 16.0, -16.0, 0.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 521),
    Shape('3038', 'Brick Sloped 45° 2 x 3', 'slope', 3, 2, 24.0, -4.0, 24.0, -30.0, 30.0, -30.0, 10.0, True, 'z', '-', 20.0, 519),
    Shape('3684', 'Brick Sloped 75° 2 x 2 x 3 [Hollow Studs]', 'slope', 2, 2, 72.0, -4.0, 72.0, -20.0, 20.0, -30.0, 10.0, True, 'z', '-', 67.0, 318),
    Shape('4460a', 'Brick Sloped 75° 2 x 1 x 3 with Open Stud', 'slope', 1, 2, 72.0, -4.0, 72.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '-', 67.0, 301),
    Shape('3300', 'Brick Sloped 33° 2 x 2 Double', 'slope', 2, 2, 14.0, 10.0, 24.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 277),
    Shape('3043', 'Brick Sloped 45° 2 x 2 Double', 'slope', 2, 2, 24.0, 0.0, 24.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 262),
    Shape('2310', 'Brick Sloped 45° 2 x 1 Inverted with 2/3 Cutout', 'slope', 1, 2, 24.0, -4.0, 24.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '+', 12.0, 231),
    Shape('3299', 'Brick Sloped 33° 2 x 4 Double', 'slope', 4, 2, 14.0, 10.0, 24.0, -40.0, 40.0, -20.0, 20.0, False, None, None, 0.0, 228),
    Shape('4445', 'Brick Sloped 45° 2 x 8', 'slope', 8, 2, 24.0, -4.0, 24.0, -80.0, 80.0, -30.0, 10.0, True, 'z', '-', 20.0, 215),
    Shape('3049d', 'Brick Sloped 45° 2 x 1 Double / Inverted with Bottom Stud Holder', 'slope', 2, 2, 24.0, 0.0, 24.0, -20.0, 20.0, -10.0, 30.0, False, None, None, 0.0, 208),
    Shape('3044c', 'Brick Sloped 45° 2 x 1 Double with Inside Stud Holder', 'slope', 1, 2, 24.0, 0.0, 24.0, -10.0, 10.0, -20.0, 20.0, False, None, None, 0.0, 200),
    Shape('5404', 'Brick Sloped 18° 2 x 1 x 2/3', 'slope', 1, 2, 15.8, -15.8, 0.0, -10.0, 10.0, -20.0, 20.0, False, 'z', '-', 10.8, 186),
    Shape('3040a', 'Brick Sloped 45° 2 x 1 without Bottom Pin', 'slope', 1, 2, 24.0, -4.0, 24.0, -10.0, 10.0, -30.0, 10.0, True, 'z', '-', 20.0, 184),
    Shape('3675', 'Brick Sloped 33° 3 x 3 Double Convex', 'slope', 3, 3, 24.0, -4.0, 24.0, -10.0, 50.0, -50.0, 10.0, True, 'x', '+', 16.8, 183),
    Shape('4515', 'Brick Sloped 10° 6 x 8', 'slope', 8, 6, 24.0, 0.0, 24.0, -80.0, 80.0, -60.0, 60.0, False, 'z', '-', 17.5, 180),
    Shape('3041', 'Brick Sloped 45° 2 x 4 Double', 'slope', 4, 2, 24.0, 0.0, 24.0, -40.0, 40.0, -20.0, 20.0, False, None, None, 0.0, 164),
    Shape('92946', 'Brick Sloped 45° 2 x 1 with 2/3 Cutout [Original Version]', 'slope', 1, 2, 24.0, -16.0, 8.0, -10.0, 10.0, -20.0, 20.0, False, 'z', '-', 8.0, 157),
    Shape('3665', 'Brick Sloped Inverted 45° 2 x 1', 'slope_inverted', 1, 2, 24.0, -4.0, 24.0, -10.0, 10.0, -30.0, 10.0, True, None, None, 0.0, 3138),
    Shape('3747b', 'Brick Sloped Inverted 33° 3 x 2, Connections between Studs, Ovoid Bottom Pin', 'slope_inverted', 2, 3, 24.0, -4.0, 24.0, -20.0, 20.0, -50.0, 10.0, True, None, None, 0.0, 1227),
    Shape('4871', 'Brick Sloped Inverted 45° 4 x 2 Double with 2 x 2 Recessed', 'slope_inverted', 2, 4, 24.0, -4.0, 24.0, -20.0, 20.0, -40.0, 40.0, True, None, None, 0.0, 964),
    Shape('2449', 'Brick Sloped Inverted 75° 2 x 1 x 3', 'slope_inverted', 1, 2, 72.0, -4.0, 72.0, -10.0, 10.0, -30.0, 10.0, True, None, None, 0.0, 587),
    Shape('4287b', 'Brick Sloped Inverted 34° 3 x 1 with Internal Stopper', 'slope_inverted', 1, 3, 24.0, -4.0, 24.0, -10.0, 10.0, -50.0, 10.0, True, None, None, 0.0, 473),
    Shape('3747a', 'Brick Sloped Inverted 33° 3 x 2, No Connections between Studs, Ovoid Bottom Pin', 'slope_inverted', 2, 3, 24.0, -4.0, 24.0, -20.0, 20.0, -50.0, 10.0, True, None, None, 0.0, 464),
    Shape('52501', 'Brick Sloped Inverted 45° 6 x 1 Double with 1 x 4 Recessed', 'slope_inverted', 1, 6, 24.0, -4.0, 24.0, -10.0, 10.0, -60.0, 60.0, True, None, None, 0.0, 429),
    Shape('4287c', 'Brick Sloped Inverted 33° 3 x 1 with Internal Stopper and No Front Stud Connection', 'slope_inverted', 1, 3, 24.0, -4.0, 24.0, -10.0, 10.0, -50.0, 10.0, True, None, None, 0.0, 412),
    Shape('4287a', 'Brick Sloped Inverted 34° 3 x 1 without Internal Stopper', 'slope_inverted', 1, 3, 24.0, -4.0, 24.0, -10.0, 10.0, -50.0, 10.0, True, None, None, 0.0, 334),
    Shape('60219', 'Brick Sloped Inverted 45° 6 x 4 Double with 4 x 4 Recessed and 3 Holes', 'slope_inverted', 4, 6, 24.0, -4.0, 24.0, -40.0, 40.0, -60.0, 60.0, True, None, None, 0.0, 305),
    Shape('3676', 'Brick Sloped Inverted 45° 2 x 2 Double Convex', 'slope_inverted', 2, 2, 24.0, -4.0, 24.0, -10.0, 30.0, -30.0, 10.0, True, None, None, 0.0, 282),
    Shape('72454', 'Brick Sloped Inverted 45° 4 x 4 Double with 4 x 2 Recessed, 2 Holes', 'slope_inverted', 4, 4, 24.0, -4.0, 24.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 256),
    Shape('4854', 'Brick Sloped Inverted 45° 4 x 4 Double with 4 x 2 Recessed', 'slope_inverted', 4, 4, 24.0, -4.0, 24.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 248),
    Shape('22889', 'Brick Sloped Inverted 45° 6 x 2 Double with 2 x 4 Recessed', 'slope_inverted', 2, 6, 24.0, -4.0, 24.0, -20.0, 20.0, -60.0, 60.0, True, None, None, 0.0, 237),
    Shape('32802', 'Brick Sloped Inverted 45° 4 x 1 Double with 1 x 2 Recessed', 'slope_inverted', 1, 4, 24.0, -4.0, 24.0, -10.0, 10.0, -40.0, 40.0, True, None, None, 0.0, 215),
    Shape('3069b', 'Tile 1 x 2 with Groove', 'tile', 2, 1, 8.0, 0.0, 8.0, -20.0, 20.0, -10.0, 10.0, False, None, None, 0.0, 6428),
    Shape('2431', 'Tile 1 x 4 with Groove', 'tile', 4, 1, 8.0, 0.0, 8.0, -40.0, 40.0, -10.0, 10.0, False, None, None, 0.0, 4922),
    Shape('3068b', 'Tile 2 x 2 with Groove', 'tile', 2, 2, 8.0, 0.0, 8.0, -20.0, 20.0, -20.0, 20.0, False, None, None, 0.0, 4711),
    Shape('3070b', 'Tile 1 x 1 with Groove', 'tile', 1, 1, 8.0, 0.0, 8.0, -10.0, 10.0, -10.0, 10.0, False, None, None, 0.0, 4163),
    Shape('6636', 'Tile 1 x 6 with Groove', 'tile', 6, 1, 8.0, 0.0, 8.0, -60.0, 60.0, -10.0, 10.0, False, None, None, 0.0, 3299),
    Shape('87079', 'Tile 2 x 4 with Groove', 'tile', 4, 2, 8.0, 0.0, 8.0, -40.0, 40.0, -20.0, 20.0, False, None, None, 0.0, 3162),
    Shape('4162', 'Tile 1 x 8 with Groove', 'tile', 8, 1, 8.0, 0.0, 8.0, -80.0, 80.0, -10.0, 10.0, False, None, None, 0.0, 2584),
    Shape('63864', 'Tile 1 x 3', 'tile', 3, 1, 8.0, 0.0, 8.0, -30.0, 30.0, -10.0, 10.0, False, None, None, 0.0, 2498),
    Shape('26603', 'Tile 2 x 3', 'tile', 3, 2, 8.0, 0.0, 8.0, -30.0, 30.0, -20.0, 20.0, False, None, None, 0.0, 1473),
    Shape('69729', 'Tile 2 x 6', 'tile', 6, 2, 8.0, 0.0, 8.0, -60.0, 60.0, -20.0, 20.0, False, None, None, 0.0, 764),
    Shape('43722', 'Wedge Plate 3 x 2 Right', 'wedge_plate', 2, 3, 8.0, -4.0, 8.0, -20.0, 20.0, -30.0, 30.0, True, None, None, 0.0, 1622),
    Shape('43723', 'Wedge Plate 3 x 2 Left', 'wedge_plate', 2, 3, 8.0, -4.0, 8.0, -20.0, 20.0, -30.0, 30.0, True, None, None, 0.0, 1604),
    Shape('41770', 'Wedge Plate 4 x 2 Left', 'wedge_plate', 2, 4, 8.0, -4.0, 8.0, -20.0, 20.0, -40.0, 40.0, True, None, None, 0.0, 1579),
    Shape('41769', 'Wedge Plate 4 x 2 Right', 'wedge_plate', 2, 4, 8.0, -4.0, 8.0, -20.0, 20.0, -40.0, 40.0, True, None, None, 0.0, 1566),
    Shape('26601', 'Wedge Plate 2 x 2 Cut Corner', 'wedge_plate', 2, 2, 8.0, -4.0, 8.0, -20.0, 20.0, -20.0, 20.0, True, None, None, 0.0, 1245),
    Shape('2450', 'Wedge Plate 3 x 3 Cut Corner', 'wedge_plate', 3, 3, 8.0, -4.0, 8.0, -30.0, 30.0, -30.0, 30.0, True, None, None, 0.0, 1203),
    Shape('2419', 'Wedge Plate 3 x 6 Cut Corners', 'wedge_plate', 6, 3, 8.0, -4.0, 8.0, -60.0, 60.0, -30.0, 30.0, True, None, None, 0.0, 1033),
    Shape('30503', 'Wedge Plate 4 x 4 Cut Corner', 'wedge_plate', 4, 4, 8.0, -4.0, 8.0, -40.0, 40.0, -40.0, 40.0, True, None, None, 0.0, 734),
    Shape('54383', 'Wedge Plate 6 x 3 Right', 'wedge_plate', 3, 6, 8.0, -4.0, 8.0, -29.0, 30.0, -60.0, 60.0, True, None, None, 0.0, 714),
    Shape('54384', 'Wedge Plate 6 x 3 Left', 'wedge_plate', 3, 6, 8.0, -4.0, 8.0, -30.0, 29.0, -60.0, 60.0, True, None, None, 0.0, 691),
    Shape('50304', 'Wedge Plate 8 x 3, 22° Right', 'wedge_plate', 3, 8, 8.0, -4.0, 8.0, -30.0, 30.0, -80.0, 80.0, True, None, None, 0.0, 470),
    Shape('50305', 'Wedge Plate 8 x 3, 22° Left', 'wedge_plate', 3, 8, 8.0, -4.0, 8.0, -30.0, 30.0, -80.0, 80.0, True, None, None, 0.0, 466),
    Shape('43719', 'Wedge Plate 4 x 4 with 2 x 2 Cutout', 'wedge_plate', 4, 4, 8.0, -4.0, 8.0, -40.0, 40.0, -20.0, 60.0, True, None, None, 0.0, 436),
    Shape('6106', 'Wedge Plate 6 x 6 Cut Corner', 'wedge_plate', 6, 6, 8.0, -4.0, 8.0, -60.0, 60.0, -60.0, 60.0, True, None, None, 0.0, 405),
    Shape('32059', 'Wedge Plate 4 x 6 Cut Corners', 'wedge_plate', 6, 4, 8.0, -4.0, 8.0, -60.0, 60.0, -40.0, 40.0, True, None, None, 0.0, 401),
    Shape('47397', 'Wedge Plate 12 x 3 Left', 'wedge_plate', 3, 12, 8.0, -4.0, 8.0, -30.0, 30.0, -120.0, 120.0, True, None, None, 0.0, 328),
    Shape('4859', 'Wedge Plate 3 x 4 without Stud Notches', 'wedge_plate', 4, 3, 8.0, -4.0, 8.0, -40.0, 40.0, -20.0, 40.0, True, None, None, 0.0, 325),
    Shape('47398', 'Wedge Plate 12 x 3 Right', 'wedge_plate', 3, 12, 8.0, -4.0, 8.0, -30.0, 30.0, -120.0, 120.0, True, None, None, 0.0, 323),
    Shape('30356', 'Wedge Plate 6 x 12 Right', 'wedge_plate', 6, 12, 8.0, -4.0, 8.0, -60.0, 60.0, -120.0, 120.0, True, None, None, 0.0, 253),
    Shape('30355', 'Wedge Plate 6 x 12 Left', 'wedge_plate', 6, 12, 8.0, -4.0, 8.0, -60.0, 60.0, -120.0, 120.0, True, None, None, 0.0, 252),
    Shape('30504', 'Wedge Plate 8 x 8 Cut Corner', 'wedge_plate', 8, 8, 8.0, -4.0, 8.0, -80.0, 80.0, -80.0, 80.0, True, None, None, 0.0, 210),
    Shape('78443', 'Wedge Plate 6 x 2 Left', 'wedge_plate', 2, 6, 8.0, -4.0, 8.0, -20.0, 19.5, -60.0, 60.0, True, None, None, 0.0, 183),
    Shape('78444', 'Wedge Plate 6 x 2 Right', 'wedge_plate', 2, 6, 8.0, -4.0, 8.0, -19.5, 20.0, -60.0, 60.0, True, None, None, 0.0, 181),
]

BY_PART: dict[str, Shape] = {s.part_num: s for s in SHAPES}


def family(name: str) -> list[Shape]:
    """Every shape in one family, commonest first."""
    return [s for s in SHAPES if s.family == name]


def fitting(name: str, width: int, depth: int) -> list[Shape]:
    """Shapes in a family with exactly this footprint, commonest first."""
    return [s for s in family(name) if s.width == width and s.depth == depth]


FAMILIES: tuple[str, ...] = ('arch', 'brick', 'cone', 'curved', 'dish', 'panel', 'plate', 'round_brick', 'round_plate', 'round_tile', 'slope', 'slope_inverted', 'tile', 'wedge_plate')
