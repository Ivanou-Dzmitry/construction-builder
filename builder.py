"""Geometry for ConstructionBuilder: slabs, columns, walls, shafts, stairs, formwork, railings, lamps
and debris, plus the UV packing and the ID mask.

Geometry (bmesh) and mesh data only, no UI here.

The building is described as a footprint: a set of (i, j) module cells on a grid. A rectangle, an L
and a U differ only in the set `footprint_cells` returns.

Русский: Геометрия ConstructionBuilder: плиты, колонны, стены, шахты,
лестницы, опалубка, ограждения, лампы и мусор, а также упаковка UV и
ID-маска. Здесь только геометрия (bmesh) и данные меша, интерфейса нет.
Здание задаётся площадью застройки: набором ячеек-модулей (i, j) на сетке.
Прямоугольник, Г и П отличаются только набором, который возвращает
`footprint_cells`.
"""

import bisect
import math
import random

import bmesh
import bpy
from mathutils import Vector

FLOORS_NAME = "CB_Floors"
COLUMNS_NAME = "CB_Columns"
WALLS_NAME = "CB_Walls"
SHAFTS_NAME = "CB_Shafts"
DEBRIS_NAME = "CB_Debris"
LAMPS_NAME = "CB_Lamps"
STAIRS_NAME = "CB_Stairs"
FORMWORK_NAME = "CB_Formwork"
FORMWORK_BEAMS_NAME = "CB_FormworkBeams"
RAILINGS_NAME = "CB_Railings"
ID_IMAGE_NAME = "CB_ID"
BUILDING_NAME = "CB_Building"
COLLECTION_NAME = "ConstructionBuilder"

MERGE_DISTANCE = 1e-5


def footprint_cells(props):
    """The set of (i, j) module cells the building stands on.

    Rectangle, or a rectangle with a block of modules cut out of the bottom
    (-Y) side, seen from above:
      L (Г): the block is cut from the bottom-right corner, leaving a top bar
             and a left leg.
      U (П): the block is cut from the middle of the bottom side, leaving a top
             bar and two legs.
    `shape_cut_x` / `shape_cut_y` (modules) are limited so the building always
    keeps a bar and at least one leg (two for U).

    Русский: Набор ячеек-модулей (i, j), на которых стоит здание.
    Прямоугольник или прямоугольник с вырезанным снизу (со стороны -Y)
    блоком модулей, вид сверху. L (Г): блок вырезан из правого нижнего угла,
    остаются верхняя перемычка и левая нога. U (П): блок вырезан из середины
    нижней стороны, остаются верхняя перемычка и две ноги. `shape_cut_x` /
    `shape_cut_y` (в модулях) ограничиваются так, чтобы всегда оставались
    перемычка и хотя бы одна нога (две для П).
    """
    nx, ny = props.modules_x, props.modules_y
    cells = {(i, j) for i in range(nx) for j in range(ny)}
    cut_y = min(props.shape_cut_y, ny - 1)
    if props.shape == "L":
        cut_x = min(props.shape_cut_x, nx - 1)
        if cut_x < 1 or cut_y < 1:
            return cells
        return {c for c in cells if not (c[0] >= nx - cut_x and c[1] < cut_y)}
    if props.shape == "U":
        cut_x = min(props.shape_cut_x, nx - 2)
        if cut_x < 1 or cut_y < 1:
            return cells
        left = (nx - cut_x) // 2
        return {c for c in cells if not (left <= c[0] < left + cut_x and c[1] < cut_y)}
    return cells


def _nearest_free(target, footprint, taken, prefer=None):
    """The footprint cell closest to `target` that is not in `taken` (or None).

    With `prefer` (a function of a cell), cells it accepts win over the rest; if
    none is accepted, any free cell is used.

    Русский: Ближайшая к `target` ячейка здания, которой нет в `taken` (или
    None). С `prefer` (функция от ячейки) подходящие ячейки важнее
    остальных; если подходящих нет, берётся любая свободная.
    """
    free = [c for c in footprint if c not in taken]
    if prefer is not None:
        free = [c for c in free if prefer(c)] or free
    if not free:
        return None
    return min(free, key=lambda c: ((c[0] - target[0]) ** 2 + (c[1] - target[1]) ** 2, c))


def parse_shaft_cells(text, props):
    """Parse "2,2; 3,1" (1-based module X,Y) into a set of 0-based cells.

    Returns (cells, ok). Cells outside the building are dropped and make `ok`
    False, as does any token that cannot be read.

    Русский: Разбирает строку "2,2; 3,1" (модули X,Y, счёт от 1) в набор
    ячеек со счётом от 0. Возвращает (ячейки, ok). Ячейки вне здания
    отбрасываются и делают ok ложным, как и любой нечитаемый фрагмент.
    """
    footprint = footprint_cells(props)
    cells = set()
    ok = True
    for token in text.replace("|", ";").split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            x, y = (int(t) for t in token.split(","))
        except ValueError:
            ok = False
            continue
        if (x - 1, y - 1) in footprint:
            cells.add((x - 1, y - 1))
        else:
            ok = False
    return cells, ok


def shaft_layout(props):
    """Where the shafts stand: returns (0-based module cells, ok).

    By default `shaft_count` shafts are placed in a row along X, in the middle
    row of the building, centred on the building. `shaft_padding` (metres, as a
    whole number of modules) is the clear gap between neighbouring shafts. A
    non-empty `shaft_cells` list overrides this and sets the modules by hand.

    Русский: Где стоят шахты: возвращает (ячейки модулей со счётом от 0,
    ok). По умолчанию `shaft_count` шахт стоят в ряд вдоль X, в среднем ряду
    здания, по центру. `shaft_padding` (метры, округляется до целых модулей)
    это свободный промежуток между соседними шахтами. Непустой `shaft_cells`
    отменяет это и задаёт модули вручную.
    """
    if props.shaft_cells.strip():
        return parse_shaft_cells(props.shaft_cells, props)
    gap = max(round(props.shaft_padding / props.module_size), 0)
    count = props.shaft_count
    span = count + (count - 1) * gap
    start = (props.modules_x - span) // 2
    row = props.modules_y // 2
    footprint = footprint_cells(props)
    cells = set()
    for k in range(count):
        target = (start + k * (1 + gap), row)
        if 0 <= target[0] < props.modules_x:
            # an L or U building may have no module there: take the nearest one
            # у Г- или П-образного здания там может не быть модуля: берём ближайший
            cell = _nearest_free(target, footprint, cells)
            if cell is not None:
                cells.add(cell)
    return cells, start >= 0 and len(cells) == count


def shaft_cells(props):
    """Modules taken by shafts (empty when shafts are off).

    Русский: Модули, занятые шахтами (пусто, если шахты выключены).
    """
    if not props.shafts:
        return set()
    return shaft_layout(props)[0]


def stair_sign(footprint, i, j):
    """+1: the stair at module (i, j) starts at its -Y side, -1: at its +Y side.

    It starts at the side that touches the rest of the building, so it arrives
    on a slab.

    Русский: +1: лестница в модуле (i, j) начинается с его стороны -Y, -1:
    со стороны +Y. Она начинается со стороны, которая касается остального
    здания, чтобы выходить на плиту.
    """
    return 1 if ((i, j - 1) in footprint or (i, j + 1) not in footprint) else -1


def stair_cells(props):
    """Modules with a fire stair (a hole through every slab), 0-based.

    `stairs_position`: CENTER (one stair in the middle of the building), EDGE
    (one at the -X end) or ENDS (one at each end along X). The target is the
    middle row; if the building has no module there (L or U shape) or a shaft
    stands there, the nearest free module is taken, preferring one that has a
    neighbour above or below, so the stair can arrive on a slab.

    Русский: Модули с пожарной лестницей (дыра во всех плитах), счёт от 0.
    `stairs_position`: CENTER (одна по центру здания), EDGE (одна у торца
    -X) или ENDS (по одной на каждом торце вдоль X). Целевой ряд средний;
    если в нём у здания нет модуля (формы Г и П) или там стоит шахта,
    берётся ближайший свободный, лучше такой, у которого есть сосед сверху
    или снизу, чтобы лестница выходила на плиту.
    """
    if not props.stairs:
        return set()
    nx, ny = props.modules_x, props.modules_y
    row = ny // 2
    targets = {
        "CENTER": [(nx // 2, row)],
        "EDGE": [(0, row)],
        "ENDS": [(0, row), (nx - 1, row)],
    }[props.stairs_position]
    footprint = footprint_cells(props)
    taken = set(shaft_cells(props))
    cells = set()

    def has_neighbour_in_y(cell):  # a stair runs along Y and must arrive on a slab / лестница идёт вдоль Y и должна выходить на плиту
        return (cell[0], cell[1] - 1) in footprint or (cell[0], cell[1] + 1) in footprint

    for target in targets:
        cell = _nearest_free(target, footprint, taken | cells, prefer=has_neighbour_in_y)
        if cell is not None:
            cells.add(cell)
    return cells


def podium_extra(props):
    """How much taller than a normal storey the first storey is (0 without a podium).

    Русский: На сколько первый этаж выше обычного (0 без стилобата).
    """
    return (props.podium_levels - 1) * props.floor_height if props.podium else 0.0


def slab_top(props, k):
    """Z of the top of slab k. Slab 0 is the ground, at Z = 0.

    Without a podium every storey is `floor_height` high. With one, the first
    storey is `podium_levels` times that, so everything above it moves up.

    Русский: Z верха плиты k. Плита 0 это земля, Z = 0. Без стилобата каждый
    этаж высотой `floor_height`. Со стилобатом первый этаж в `podium_levels`
    раз выше, поэтому всё над ним поднимается.
    """
    return 0.0 if k <= 0 else k * props.floor_height + podium_extra(props)


def total_height(props):
    """Z of the top of the roof slab.

    Русский: Z верха плиты крыши.
    """
    return slab_top(props, props.floors)


def detail_weights(props):
    """{module: weight 0..1} that makes random details gather near the edge.

    A module on the outer ring of the building (or on the edge of a notch) has
    weight 1. The weight falls towards the middle of the building, down to
    `1 - edge_bias` in the deepest module: the centre is seen anyway and gets
    fewer details. Lamps, debris and holes multiply their chance by it.

    Русский: {модуль: вес 0..1}, из-за которого случайные детали собираются
    у края. У модуля на внешнем кольце здания (или на краю выреза) вес 1. К
    середине здания вес падает до `1 - edge_bias` в самом глубоком модуле:
    центр и так виден, деталей там меньше. Шанс ламп, мусора и отверстий
    умножается на вес.
    """
    footprint = footprint_cells(props)
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    depth = {c: 0 for c in footprint if any((c[0] + dx, c[1] + dy) not in footprint for dx, dy in sides)}
    queue = list(depth)
    while queue:
        cell = queue.pop(0)
        for dx, dy in sides:
            n = (cell[0] + dx, cell[1] + dy)
            if n in footprint and n not in depth:
                depth[n] = depth[cell] + 1
                queue.append(n)
    deepest = max(depth.values(), default=0)
    return {c: 1.0 - props.edge_bias * (d / deepest if deepest else 0.0) for c, d in depth.items()}


def _rects_overlap(a, b):
    """Do two rectangles (x0, y0, x1, y1) overlap?

    Русский: Пересекаются ли два прямоугольника (x0, y0, x1, y1)?
    """
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _hole_blocks(hole, x, y, radius):
    """Does a hole (x0, y0, x1, y1) touch the square of half-size `radius` at (x, y)?

    Русский: Задевает ли отверстие (x0, y0, x1, y1) квадрат с полуразмером
    `radius` в точке (x, y)?
    """
    return _rects_overlap(hole, (x - radius, y - radius, x + radius, y + radius))


HOLE_MARGIN = 0.35  # metres: a hole keeps this far from the module edge (columns, railings) / метры: отверстие держится на таком расстоянии от края модуля (колонны, ограждения)


def slab_holes(props):
    """Random square holes (for pipes and such) in some upper slabs.

    Returns {(slab, module): (x0, y0, x1, y1)} in building coordinates. Every
    module of slab 1..floors (shafts and stairs excluded) may get one square hole
    with probability `hole_factor` times the module's edge weight, so holes
    gather near the edge. A hole in a module on the outer edge sits close to
    that edge; in the middle it can be anywhere. Seeded per (slab, module).

    Русский: Случайные квадратные отверстия (для труб и т. п.) в некоторых
    верхних плитах. Возвращает {(плита, модуль): (x0, y0, x1, y1)} в
    координатах здания. Каждый модуль плит 1..floors (кроме шахт и лестниц)
    может получить одно квадратное отверстие с вероятностью `hole_factor` на
    вес модуля, поэтому отверстия собираются у края. В модуле на внешнем
    краю отверстие сидит близко к этому краю, в середине где угодно. Зерно
    на (плита, модуль).
    """
    if not props.slab_holes:
        return {}
    size = props.module_size
    footprint = footprint_cells(props)
    cells = footprint - shaft_cells(props) - stair_cells(props)
    weights = detail_weights(props)
    seed = props.random_seed
    low, high = sorted(props.hole_size)
    free = size - 2 * HOLE_MARGIN
    holes = {}
    if free < 0.2:
        return holes
    for slab in range(1, props.floors + 1):
        for i, j in sorted(cells):
            if _roll(seed, "hole", slab, i, j) >= props.hole_factor * weights[(i, j)]:
                continue
            rng = random.Random(f"{seed}|hole-shape|{slab}|{i}|{j}")
            side = min(rng.uniform(low, high), free)
            outer = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (i + dx, j + dy) not in footprint]
            x0 = i * size + HOLE_MARGIN + rng.uniform(0.0, free - side)
            y0 = j * size + HOLE_MARGIN + rng.uniform(0.0, free - side)
            if outer:  # close to the outer edge of the building / близко к наружному краю здания
                dx, dy = rng.choice(outer)
                near = min(rng.uniform(0.0, 0.5), free - side)
                if dx:
                    x0 = i * size + (HOLE_MARGIN + near if dx < 0 else size - HOLE_MARGIN - near - side)
                else:
                    y0 = j * size + (HOLE_MARGIN + near if dy < 0 else size - HOLE_MARGIN - near - side)
            holes[(slab, (i, j))] = (x0, y0, x0 + side, y0 + side)
    return holes


def _add_box(bm, lo, hi, sides=(True, True, True, True), bottom=True, top=True):
    """Add an axis-aligned box and return its faces.

    `sides` = (-X, +X, -Y, +Y). A side flagged False gets no polygons: that is
    where a slab module is stitched to its neighbour. `bottom=False` drops the
    bottom face (a rebar's bottom is buried inside the column), `top=False` the
    top face (a lamp's top is against the ceiling).

    Русский: Добавляет бокс по осям и возвращает его грани. `sides` = (-X,
    +X, -Y, +Y). Сторона с False не получает полигонов: там модуль плиты
    сшит с соседом. `bottom=False` убирает нижнюю грань (низ прута спрятан в
    колонне), `top=False` верхнюю (верх лампы у потолка).
    """
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = {
        "000": bm.verts.new((x0, y0, z0)),
        "100": bm.verts.new((x1, y0, z0)),
        "110": bm.verts.new((x1, y1, z0)),
        "010": bm.verts.new((x0, y1, z0)),
        "001": bm.verts.new((x0, y0, z1)),
        "101": bm.verts.new((x1, y0, z1)),
        "111": bm.verts.new((x1, y1, z1)),
        "011": bm.verts.new((x0, y1, z1)),
    }
    faces = [("001", "101", "111", "011")] if top else []
    if bottom:
        faces.append(("000", "010", "110", "100"))
    neg_x, pos_x, neg_y, pos_y = sides
    if neg_x:
        faces.append(("010", "000", "001", "011"))
    if pos_x:
        faces.append(("100", "110", "111", "101"))
    if neg_y:
        faces.append(("000", "100", "101", "001"))
    if pos_y:
        faces.append(("110", "010", "011", "111"))
    made = [bm.faces.new([v[n] for n in names]) for names in faces]
    for vert in v.values():  # a corner no face uses would stay behind as a loose vertex / угол, который не использует ни одна грань, остался бы висящей вершиной
        if not vert.link_faces:
            bm.verts.remove(vert)
    return made


def _add_slab_with_hole(bm, lo, hi, hole, sides):
    """A slab module with a square hole through it.

    The top and the bottom are each a ring of four quads between the module edge
    and the hole; the hole has four walls. `sides` is as in _add_box.

    Русский: Модуль плиты со сквозным квадратным отверстием. Верх и низ это
    по кольцу из четырёх четырёхугольников между краем модуля и отверстием;
    у отверстия четыре стенки. `sides` как в _add_box.
    """
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    hx0, hy0, hx1, hy1 = hole
    outer = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    inner = ((hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1))
    top_out = [bm.verts.new((x, y, z1)) for x, y in outer]
    top_in = [bm.verts.new((x, y, z1)) for x, y in inner]
    bottom_out = [bm.verts.new((x, y, z0)) for x, y in outer]
    bottom_in = [bm.verts.new((x, y, z0)) for x, y in inner]
    centre = ((hx0 + hx1) / 2, (hy0 + hy1) / 2)

    def face(verts, direction):
        made = bm.faces.new(verts)
        made.normal_update()
        if made.normal.dot(direction) < 0:
            made.normal_flip()

    for k in range(4):
        n = (k + 1) % 4
        face([top_out[k], top_out[n], top_in[n], top_in[k]], (0.0, 0.0, 1.0))
        face([bottom_out[k], bottom_out[n], bottom_in[n], bottom_in[k]], (0.0, 0.0, -1.0))
        middle = ((inner[k][0] + inner[n][0]) / 2, (inner[k][1] + inner[n][1]) / 2)
        face([top_in[k], top_in[n], bottom_in[n], bottom_in[k]], (centre[0] - middle[0], centre[1] - middle[1], 0.0))
    neg_x, pos_x, neg_y, pos_y = sides
    if neg_x:
        face([top_out[3], top_out[0], bottom_out[0], bottom_out[3]], (-1.0, 0.0, 0.0))
    if pos_x:
        face([top_out[1], top_out[2], bottom_out[2], bottom_out[1]], (1.0, 0.0, 0.0))
    if neg_y:
        face([top_out[0], top_out[1], bottom_out[1], bottom_out[0]], (0.0, -1.0, 0.0))
    if pos_y:
        face([top_out[2], top_out[3], bottom_out[3], bottom_out[2]], (0.0, 1.0, 0.0))


def build_floors(props, offset):
    """All floor slabs, every module stitched into one mesh.

    Slabs 1..floors have a hole under every shaft and stair, and a random square
    hole here and there (see slab_holes). With `ground_slab` there is also a slab
    at ground level, with its top at Z = 0. It is solid, so shafts and stairs
    stand on it. Its underside is in the ground, so it has no bottom face; the
    top and the edges (the thickness) stay.

    Русский: Все плиты перекрытий, каждый модуль сшит в один меш. В плитах
    1..floors есть дыра под каждой шахтой и лестницей и кое-где случайное
    квадратное отверстие (см. slab_holes). С `ground_slab` есть ещё плита на
    уровне земли, её верх на Z = 0. Она сплошная, поэтому шахты и лестницы
    стоят на ней. Её низ в земле, так что нижней грани нет; верх и торцы
    (толщина) остаются.
    """
    size = props.module_size
    footprint = footprint_cells(props)
    upper = footprint - shaft_cells(props) - stair_cells(props)  # holes / дыры
    holes = slab_holes(props)
    ox, oy = offset
    bm = bmesh.new()

    def add_slab(cells, z1, buried=False, slab=0):
        z0 = z1 - props.slab_thickness
        for i, j in sorted(cells):
            sides = (
                (i - 1, j) not in cells,
                (i + 1, j) not in cells,
                (i, j - 1) not in cells,
                (i, j + 1) not in cells,
            )
            lo = (i * size + ox, j * size + oy, z0)
            hi = ((i + 1) * size + ox, (j + 1) * size + oy, z1)
            hole = holes.get((slab, (i, j)))
            if hole is not None:
                shifted = (hole[0] + ox, hole[1] + oy, hole[2] + ox, hole[3] + oy)
                _add_slab_with_hole(bm, lo, hi, shifted, sides)
            else:
                _add_box(bm, lo, hi, sides, bottom=not buried)

    if props.ground_slab:
        add_slab(footprint, 0.0, buried=True)
    for floor in range(1, props.floors + 1):
        add_slab(upper, slab_top(props, floor), slab=floor)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    return bm


def build_columns(props, offset):
    """One box per grid node, ground to top, through the slabs.

    Each column rises above the top slab by `column_extension` plus a random
    0..`column_height_variation` (seeded, so a Rebuild gives the same result).
    With `rebar` on, a 3x3 group of thin boxes sticks out of every column top.

    The four corner columns of a shaft would end up inside the walls of its top
    block, with the rebar sticking out of the wall. `shaft_columns` says what to
    do with them: REMOVE (the shaft walls carry the floors), TRIM (the column
    ends at the roof slab, without rebar, below the shaft's top block) or FULL.
    A column taller than `uv_column_cut` gets an edge loop every `uv_column_cut`
    metres (for the UV cut, see unwrap); lower columns are not changed.

    Русский: Один бокс на узел сетки, от земли до верха, сквозь плиты.
    Каждая колонна поднимается над верхней плитой на `column_extension` плюс
    случайные 0..`column_height_variation` (с зерном, поэтому Rebuild даёт
    тот же результат). С `rebar` из каждой верхушки торчит группа 3×3 тонких
    боксов. Четыре угловые колонны шахты оказались бы внутри стен её
    верхнего блока, с арматурой, торчащей из стены. `shaft_columns` говорит,
    что с ними делать: REMOVE (убрать, перекрытия несут стены шахты), TRIM
    (колонна кончается на плите крыши, без арматуры, ниже верхнего блока
    шахты) или FULL. Колонна выше `uv_column_cut` получает пояс рёбер через каждые `uv_column_cut` метров (для разреза UV, см. unwrap); низкие колонны не меняются.
    """
    size = props.module_size
    cells = footprint_cells(props)
    ox, oy = offset
    nodes = set()
    for i, j in cells:
        nodes.update(((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)))
    shaft_nodes = set()
    for i, j in shaft_cells(props):
        shaft_nodes.update(((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)))
    half_x = props.column_width / 2
    half_y = props.column_depth / 2
    rng = random.Random(props.random_seed)
    bm = bmesh.new()
    for i, j in sorted(nodes):
        cx = i * size + ox
        cy = j * size + oy
        top = (  # drawn for every column, so the others never change with the shaft mode / считается для каждой колонны, поэтому остальные не меняются от режима колонн шахты
            total_height(props)
            + props.column_extension
            + rng.uniform(0.0, props.column_height_variation)
        )
        rebar = props.rebar
        if (i, j) in shaft_nodes:
            if props.shaft_columns == "REMOVE":
                continue
            if props.shaft_columns == "TRIM":
                top = total_height(props)  # ends at the roof slab / кончается на плите крыши
                rebar = False
        # no bottom face: the column foot is buried in the ground
        # нижней грани нет: пята колонны в земле
        faces = _add_box(
            bm,
            (cx - half_x, cy - half_y, 0.0),
            (cx + half_x, cy + half_y, top),
            bottom=False,
        )
        # A tall column gets an edge loop every `uv_column_cut` metres, so its UVs can be cut there:
        # one 37 m island would limit the scale of the whole tile. A lower column is not touched.
        # У высокой колонны пояс рёбер через каждые `uv_column_cut` м, чтобы резать там UV:
        # один островок в 37 м ограничил бы масштаб всего тайла. Низкая колонна не меняется.
        if props.uv_column_cut:
            geom = list(faces) + list({e for face in faces for e in face.edges}) + list({v for face in faces for v in face.verts})
            level = props.uv_column_cut
            while level < top - 0.05:
                geom = list(set(bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=(0.0, 0.0, level), plane_no=(0.0, 0.0, 1.0))["geom"]))
                level += props.uv_column_cut
        if rebar:
            _add_rebar(bm, props, cx, cy, top, random.Random(f"{props.random_seed}|rebar|{i}|{j}"))
    return bm


REBAR_EMBED = 0.05  # how far a rod starts inside the column / насколько прут начинается внутри колонны
REBAR_EDGE_GAP = 0.04  # clear distance from the column edge to a rod / расстояние в свету от края колонны до прута


def _add_rebar(bm, props, cx, cy, top, rng):
    """3x3 thin boxes on top of a column; all share one smoothing group.

    Every rod gets its own height: `rebar_height` +- `rebar_height_variation`.

    Русский: 9 тонких боксов 3×3 на верхушке колонны; все в одной группе
    сглаживания. У каждого прута своя высота: `rebar_height` ±
    `rebar_height_variation`.
    """
    rod = props.rebar_size
    reach_x = max(props.column_width / 2 - REBAR_EDGE_GAP - rod / 2, 0.0)
    reach_y = max(props.column_depth / 2 - REBAR_EDGE_GAP - rod / 2, 0.0)
    for ix in (-1, 0, 1):
        for iy in (-1, 0, 1):
            height = max(
                props.rebar_height
                + rng.uniform(-props.rebar_height_variation, props.rebar_height_variation),
                0.01,
            )
            rx = cx + ix * reach_x
            ry = cy + iy * reach_y
            faces = _add_box(
                bm,
                (rx - rod / 2, ry - rod / 2, top - REBAR_EMBED),
                (rx + rod / 2, ry + rod / 2, top + height),
                bottom=False,
            )
            for face in faces:
                face.smooth = True


def parse_floor_set(text, max_floor):
    """Parse "1-3, 5" or "all" into a set of floor numbers (1..max_floor).

    Returns (floors, ok). `ok` is False if some token could not be read.

    Русский: Разбирает "1-3, 5" или "all" в набор номеров этажей
    (1..max_floor). Возвращает (этажи, ok). `ok` ложно, если какой-то
    фрагмент не прочитан.
    """
    text = text.strip().lower()
    if text in ("all", "*"):
        return set(range(1, max_floor + 1)), True
    floors = set()
    ok = True
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            if "-" in token:
                lo, hi = (int(t) for t in token.split("-", 1))
                floors.update(range(min(lo, hi), max(lo, hi) + 1))
            else:
                floors.add(int(token))
        except ValueError:
            ok = False
    return {f for f in floors if 1 <= f <= max_floor}, ok


def _wall_point(axis, a, p, z):
    """Point on a wall: `a` runs along the wall, `p` across it.

    Русский: Точка на стене: `a` идёт вдоль стены, `p` поперёк.
    """
    return (a, p, z) if axis == "x" else (p, a, z)


def _wall_face(bm, points, direction):
    """Add a face and flip it if it does not look along `direction`.

    Русский: Добавляет грань и переворачивает её, если она не смотрит вдоль
    `direction`.
    """
    face = bm.faces.new([bm.verts.new(pt) for pt in points])
    face.normal_update()
    if face.normal.dot(direction) < 0:
        face.normal_flip()
    return face


def _wall_outlines(a0, a1, z0, z1, door):
    """Face outlines (lists of (along, z)) of a wall piece, solid or with a door.

    A door gives three quads. The splits run from the top corners of the piece
    to the top corners of the opening, so no extra vertices sit on the top edge.

    Русский: Контуры граней (списки (вдоль, z)) куска стены, глухого или с
    дверью. Дверь даёт три четырёхугольника. Разрезы идут от верхних углов
    куска к верхним углам проёма, поэтому на верхнем ребре нет лишних
    вершин.
    """
    if door is None:
        return [[(a0, z0), (a1, z0), (a1, z1), (a0, z1)]]
    d0, d1, zd = door
    return [
        [(a0, z0), (d0, z0), (d0, zd), (a0, z1)],
        [(a0, z1), (d0, zd), (d1, zd), (a1, z1)],
        [(d1, z0), (a1, z0), (a1, z1), (d1, zd)],
    ]


def _door_reveals(bm, axis, p0, p1, door, z0):
    """Jambs and lintel underside of a door opening between planes p0 and p1.

    Русский: Откосы и низ перемычки дверного проёма между плоскостями p0 и
    p1.
    """
    d0, d1, zd = door
    along = (1.0, 0.0, 0.0) if axis == "x" else (0.0, 1.0, 0.0)
    neg_along = tuple(-c for c in along)
    for a, direction in ((d0, along), (d1, neg_along)):  # jambs / откосы
        _wall_face(
            bm,
            [
                _wall_point(axis, a, p0, z0),
                _wall_point(axis, a, p1, z0),
                _wall_point(axis, a, p1, zd),
                _wall_point(axis, a, p0, zd),
            ],
            direction,
        )
    _wall_face(  # underside of the lintel / низ перемычки
        bm,
        [
            _wall_point(axis, d0, p0, zd),
            _wall_point(axis, d1, p0, zd),
            _wall_point(axis, d1, p1, zd),
            _wall_point(axis, d0, p1, zd),
        ],
        (0.0, 0.0, -1.0),
    )


def _add_wall(bm, axis, fixed, a0, a1, z0, z1, thickness, door):
    """One wall piece between two columns.

    Only the visible surfaces are built: both sides and, for a door, the two
    jambs and the underside of the lintel. The ends touch the columns and the
    top and bottom touch the slabs, so those faces would be hidden anyway.
    `door` is None for a solid wall, or (d0, d1, door_top).

    Русский: Один кусок стены между двумя колоннами. Строятся только видимые
    поверхности: обе стороны и, для двери, два откоса и низ перемычки. Торцы
    касаются колонн, а верх и низ касаются плит, так что эти грани всё равно
    были бы скрыты. `door` равно None для глухой стены или (d0, d1,
    door_top).
    """
    p0 = fixed - thickness / 2
    p1 = fixed + thickness / 2
    across = (0.0, 1.0, 0.0) if axis == "x" else (1.0, 0.0, 0.0)
    neg_across = tuple(-c for c in across)

    def side(p, direction, outline):
        """One face on plane `p`; `outline` is a list of (along, z) points."""
        _wall_face(
            bm, [_wall_point(axis, a, p, z) for a, z in outline], direction
        )

    for outline in _wall_outlines(a0, a1, z0, z1, door):
        side(p1, across, outline)
        side(p0, neg_across, outline)

    if door is not None:
        _door_reveals(bm, axis, p0, p1, door, z0)


def _roll(seed, *key):
    """A repeatable random number in 0..1 for one element (a wall, a door).

    It depends only on the seed and the element's own key, so changing other
    settings (floors with walls, Clear Walls, Wall Chance) never reshuffles it.

    Русский: Повторяемое случайное число 0..1 для одного элемента (стены,
    двери). Зависит только от зерна и ключа самого элемента, поэтому смена
    других настроек (этажей со стенами, Clear Walls, Wall Chance) его не
    перемешивает.
    """
    return random.Random("|".join(str(part) for part in (seed, *key))).random()


def build_walls(props, offset):
    """Interior walls only: at most one per inner grid edge, per selected floor.

    A wall stands between two columns and between two slabs. `wall_chance` is
    the share of inner edges that get a wall (the same on every floor, so rooms
    stack). Each wall is solid or has a door, random with `door_chance`. All
    choices are seeded per element, so they repeat on every Rebuild.

    Русский: Только внутренние стены: не больше одной на каждое внутреннее
    ребро сетки, на каждом выбранном этаже. Стена стоит между двумя
    колоннами и между двумя плитами. `wall_chance` это доля внутренних рёбер
    со стеной (одинакова на всех этажах, комнаты стоят друг над другом).
    Каждая стена глухая или с дверью, случайно с `door_chance`. Все выборы
    привязаны к элементу и зерну, поэтому повторяются при каждом Rebuild.
    """
    size = props.module_size
    cells = footprint_cells(props)
    ox, oy = offset
    floors, _ok = parse_floor_set(props.wall_floors, props.floors)
    if props.podium:  # no partitions on the podium floor: walls start from floor 2 / на этаже стилобата перегородок нет: стены начинаются со 2-го этажа
        floors = {f for f in floors if f > 1}
    seed = props.random_seed
    thickness = props.wall_thickness

    # No partitions around the shafts, so they stay visible: every module within
    # `shaft_clear_radius` of a shaft (the shaft itself included) is left open.
    # Вокруг шахт перегородок нет, чтобы шахты были видны: каждый модуль в пределах
    # `shaft_clear_radius` от шахты (сама шахта тоже) остаётся открытым.
    radius = props.shaft_clear_radius
    cleared = {
        (i + di, j + dj)
        for i, j in shaft_cells(props)
        for di in range(-radius, radius + 1)
        for dj in range(-radius, radius + 1)
    }

    cleared |= stair_cells(props)  # a stairwell is left open too / лестничная клетка тоже остаётся открытой

    def wanted(axis, i, j, other):
        if other not in cells or (i, j) in cleared or other in cleared:
            return False
        return _roll(seed, "wall", axis, i, j) < props.wall_chance

    edges = []  # (axis, fixed, start, end, half column along the wall, key) / (ось, линия, начало, конец, половина колонны вдоль стены, ключ)
    for i, j in sorted(cells):
        if wanted("x", i, j, (i, j + 1)):  # wall along X, between two rows / стена вдоль X, между двумя рядами
            edges.append(("x", (j + 1) * size, i * size, (i + 1) * size, props.column_width / 2, (i, j)))
        if wanted("y", i, j, (i + 1, j)):  # wall along Y, between two columns / стена вдоль Y, между двумя столбцами модулей
            edges.append(("y", (i + 1) * size, j * size, (j + 1) * size, props.column_depth / 2, (i, j)))

    bm = bmesh.new()
    for axis, fixed, start, end, half, (ci, cj) in edges:
        a0 = start + half
        a1 = end - half
        length = a1 - a0
        for floor in sorted(floors):
            z0 = slab_top(props, floor - 1)
            z1 = slab_top(props, floor) - props.slab_thickness
            storey_h = z1 - z0
            if length <= 0.0 or storey_h <= 0.0:
                continue
            is_door = _roll(seed, "door", axis, ci, cj, floor) < props.door_chance
            door = None
            door_width = min(props.door_width, length - 0.2)
            if is_door and door_width >= 0.3 and storey_h > 0.3:
                mid = (a0 + a1) / 2
                door_top = z0 + min(props.door_height, storey_h - 0.1)
                door = (mid - door_width / 2, mid + door_width / 2, door_top)
            _add_wall(bm, axis, fixed, a0, a1, z0, z1, thickness, door)

    # shift to the building origin (Center on Origin) without touching the maths above
    # сдвиг к началу здания (Center on Origin), не трогая расчёт выше
    for v in bm.verts:
        v.co.x += ox
        v.co.y += oy
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    return bm


MIN_DOOR_STOREY = 1.5  # a shaft floor lower than this (metres) gets no door / этаж шахты ниже этого значения (м) двери не получает


SHAFT_SIDES = (  # (axis, outward sign, name) / (ось, знак наружу, имя)
    ("x", -1, "-Y"),
    ("x", 1, "+Y"),
    ("y", -1, "-X"),
    ("y", 1, "+X"),
)


def _shaft_levels(props):
    """Vertical segments of a shaft wall: [(z_lo, z_hi, is_storey)].

    Storeys alternate with slab bands, so every side has vertices at the same
    heights (no T-junctions on the corner edges). Storeys can carry a door. The
    last segment is the top block above the roof (`shaft_extension` high): the
    shaft's last floor, which gets a door too.

    Русский: Вертикальные отрезки стены шахты: [(z_низ, z_верх, этаж ли)].
    Этажи чередуются с полосами перекрытий, поэтому у всех сторон вершины на
    одних высотах (нет T-вершин на угловых рёбрах). Этаж может нести дверь.
    Последний отрезок это верхний блок над крышей (высотой
    `shaft_extension`): последний этаж шахты, в нём тоже есть дверь.
    """
    floor_h = props.floor_height
    slab = props.slab_thickness
    roof = total_height(props)
    top = roof + props.shaft_extension
    if floor_h - slab <= 0.3:  # no room for a door: one plain wall / для двери нет места: одна глухая стена
        return [(0.0, top, False)]
    segments = []
    for k in range(1, props.floors + 1):
        z1 = slab_top(props, k) - slab
        segments.append((slab_top(props, k - 1), z1, True))
        segments.append((z1, slab_top(props, k), False))  # the slab band / полоса перекрытия
    if top > roof + 1e-6:  # the top block: the last shaft floor, standing on the roof / верхний блок: последний этаж шахты, стоит на крыше
        segments.append((roof, top, True))
    return segments


def _add_shaft_side(bm, axis, centre, sign, c0, c1, half, segments, door_props):
    """One side of the tube. `door_props` is set on the side that gets doors.

    Русский: Одна сторона трубы. `door_props` задан у стороны, где есть
    двери.
    """
    p_out = centre + sign * half
    p_in = centre - sign * half
    out_dir = (0.0, sign, 0.0) if axis == "x" else (sign, 0.0, 0.0)
    in_dir = tuple(-c for c in out_dir)
    ranges = ((c0 - half, c1 + half, p_out, out_dir), (c0 + half, c1 - half, p_in, in_dir))

    for z_lo, z_hi, is_storey in segments:
        door = None
        if is_storey and door_props is not None and z_hi - z_lo >= MIN_DOOR_STOREY:
            width = min(door_props.door_width, (c1 - c0) - 2 * half - 0.2)
            if width >= 0.3:
                mid = (c0 + c1) / 2
                top = z_lo + min(door_props.door_height, z_hi - z_lo - 0.1)
                door = (mid - width / 2, mid + width / 2, top)
        for a0, a1, plane, direction in ranges:
            for outline in _wall_outlines(a0, a1, z_lo, z_hi, door):
                _wall_face(
                    bm,
                    [_wall_point(axis, a, plane, z) for a, z in outline],
                    direction,
                )
        if door is not None:
            _door_reveals(bm, axis, p_in, p_out, door, z_lo)


def build_shafts(props, offset):
    """Elevator shafts: a hollow tube per listed module, ground to above the roof.

    Every storey has one door, on the side set by `shaft_door_side`. The wall is
    centred on the module edge. There is no bottom face (the shaft stands in the
    ground); the top is closed with a ring.

    Русский: Лифтовые шахты: полая труба на каждый заданный модуль, от земли
    до выше крыши. На каждом этаже одна дверь, на стороне `shaft_door_side`.
    Стена по краю модуля. Нижней грани нет (шахта стоит в земле); сверху
    закрыто кольцом.
    """
    size = props.module_size
    half = props.shaft_thickness / 2
    segments = _shaft_levels(props)
    top = total_height(props) + props.shaft_extension
    bm = bmesh.new()
    for i, j in sorted(shaft_cells(props)):
        x0, x1 = i * size, (i + 1) * size
        y0, y1 = j * size, (j + 1) * size
        for axis, sign, name in SHAFT_SIDES:
            if axis == "x":
                centre, c0, c1 = (y0 if sign < 0 else y1), x0, x1
            else:
                centre, c0, c1 = (x0 if sign < 0 else x1), y0, y1
            door_props = props if name == props.shaft_door_side else None
            _add_shaft_side(bm, axis, centre, sign, c0, c1, half, segments, door_props)
        outer = [(x0 - half, y0 - half), (x1 + half, y0 - half), (x1 + half, y1 + half), (x0 - half, y1 + half)]
        inner = [(x0 + half, y0 + half), (x1 - half, y0 + half), (x1 - half, y1 - half), (x0 + half, y1 - half)]
        for k in range(4):
            n = (k + 1) % 4
            _wall_face(  # top ring / верхнее кольцо
                bm,
                [(*outer[k], top), (*outer[n], top), (*inner[n], top), (*inner[k], top)],
                (0.0, 0.0, 1.0),
            )
    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    return bm


def build_debris(props, offset):
    """Construction debris: boxes standing on the slabs (bricks, pallets...).

    Every module on the selected floors (`debris_floors`) gets at most one box,
    with probability `debris_factor` times the module's edge weight (fewer boxes
    in the middle of the building). Floor k is the floor of storey k, the same
    numbering as `wall_floors`: 1 is the ground, `floors` + 1 is the roof. The size is random inside the ranges
    set in the panel. The box is kept inside its module, inset from the module
    edges, so it stays clear of the columns and walls; shaft holes get none.
    A box has no bottom face: it stands on the slab or the ground. Every choice is seeded per
    (floor, module), so a Rebuild repeats it and changing other settings does
    not reshuffle the rest.

    Русский: Строительный мусор: боксы на плитах (кирпичи, поддоны...).
    Каждый модуль на выбранных этажах (`debris_floors`) получает не больше
    одного бокса с вероятностью `debris_factor` на вес модуля (в середине
    здания меньше). Этаж k это пол этажа k, нумерация как у `wall_floors`: 1
    земля, `floors` + 1 крыша. Размер случайный в диапазонах из панели. Бокс
    стоит внутри модуля с отступом от краёв, поэтому не задевает колонны и
    стены; над дырами шахт боксов нет. Нижней грани нет: бокс стоит на плите
    или на земле. Все выборы привязаны к (этаж, модуль) и зерну, поэтому
    Rebuild повторяет результат, а смена других настроек остальное не
    перемешивает.
    """
    size = props.module_size
    ox, oy = offset
    seed = props.random_seed
    floors, _ok = parse_floor_set(props.debris_floors, props.floors + 1)
    if props.podium:  # debris starts from floor 2, above the podium / мусор начинается со 2-го этажа, над стилобатом
        floors = {f for f in floors if f > 1}
    cells = sorted(footprint_cells(props) - shaft_cells(props) - stair_cells(props))
    h_lo, h_hi = sorted(props.debris_height)
    l_lo, l_hi = sorted(props.debris_length)
    w_lo, w_hi = sorted(props.debris_width)
    inset = max(props.column_width, props.column_depth, props.wall_thickness) / 2 + 0.1
    room = size - 2 * inset  # free length along a module side / свободная длина вдоль стороны модуля
    bm = bmesh.new()
    if not cells or room <= 0.1:
        return bm
    weights = detail_weights(props)  # fewer boxes in the middle of the building / в середине здания боксов меньше
    holes = slab_holes(props)

    for floor in sorted(floors):
        z = slab_top(props, floor - 1)  # floor of storey `floor`; 1 = ground / пол этажа `floor`; 1 = земля
        for i, j in cells:
            if _roll(seed, "debris", floor, i, j) >= props.debris_factor * weights[(i, j)]:
                continue
            rng = random.Random(f"{seed}|debris-size|{floor}|{i}|{j}")
            length = min(rng.uniform(l_lo, l_hi), room)
            width = min(rng.uniform(w_lo, w_hi), room)
            height = rng.uniform(h_lo, h_hi)
            lx, ly = (length, width) if rng.random() < 0.5 else (width, length)
            x0 = i * size + inset + rng.uniform(0.0, room - lx)
            y0 = j * size + inset + rng.uniform(0.0, room - ly)
            hole = holes.get((floor - 1, (i, j)))  # the box would stand over a hole / бокс стоял бы над отверстием
            if hole is not None and _rects_overlap(hole, (x0, y0, x0 + lx, y0 + ly)):
                continue
            _add_box(bm, (x0, y0, z), (x0 + lx, y0 + ly, z + height), bottom=False)

    for v in bm.verts:
        v.co.x += ox
        v.co.y += oy
    return bm


STAIR_RISER_TARGET = 0.19  # metres, the step height aimed for (both styles) / метры, целевая высота ступени (оба стиля)
STAIR_THICKNESS = 0.25  # metres, concrete under the steps and in the landings / метры, бетон под ступенями и в площадках
STAIR_LANDING = 0.9  # metres, depth of the half landing / метры, глубина половинной площадки


def _stair_flight(bm, xa, xb, y_origin, sign, z0, blocks, length, rise):
    """One flight as a few big boxes stepping up, touching at the corners.

    Seen from the side the blocks form a diagonal ladder: block k covers the
    k-th part of the run and the k-th part of the rise. The flight starts at
    y_origin and runs along Y in direction `sign`, rising `rise` from `z0`.

    Русский: Один марш из нескольких крупных боксов лесенкой, касающихся
    углами. Сбоку блоки образуют диагональную лестницу: блок k покрывает k-ю
    часть пути и k-ю часть подъёма. Марш начинается в y_origin и идёт вдоль
    Y в направлении `sign`, поднимаясь на `rise` от `z0`.
    """
    run = length / blocks
    step = rise / blocks
    for k in range(blocks):
        ya = y_origin + sign * k * run
        yb = y_origin + sign * (k + 1) * run
        _add_box(
            bm,
            (xa, min(ya, yb), z0 + k * step),
            (xb, max(ya, yb), z0 + (k + 1) * step),
            bottom=k > 0,  # the first block stands on the floor / первый блок стоит на полу
        )


def _stair_flight_solid(bm, xa, xb, y_origin, sign, z0, steps, tread, riser):
    """One concrete flight: steps on top of an inclined slab, like a precast flight.

    `s` runs from the low end (s = 0, at y_origin) along Y in direction `sign`
    and rises `steps * riser` from `z0`. The slab is STAIR_THICKNESS thick, so
    the underside leaves the flight exactly one slab below the top landing.
    Faces: steps, both sides and the sloped underside. The two ends are not
    capped: they touch a landing or a slab, so a cap would be hidden anyway.

    Русский: Один бетонный марш: ступени на наклонной плите, как у сборного
    марша. `s` идёт от нижнего конца (s = 0, в y_origin) вдоль Y в
    направлении `sign` и поднимается на `steps * riser` от `z0`. Плита
    толщиной STAIR_THICKNESS, поэтому низ марша приходит ровно на плиту ниже
    верхней площадки. Грани: ступени, обе стороны и скошенный низ. Торцы не
    закрыты: они упираются в площадку или плиту, и крышка всё равно была бы
    скрыта.
    """
    thick = STAIR_THICKNESS

    def pt(x, s, z):
        return (x, y_origin + sign * s, z)

    towards_low = (0.0, -sign, 0.0)
    length = steps * tread
    z_top = z0 + steps * riser

    profile = [(0.0, z0 - thick)]
    for k in range(steps):
        z = z0 + (k + 1) * riser
        profile.append((k * tread, z))
        profile.append(((k + 1) * tread, z))
    profile.append((length, z_top - thick))
    for x, direction in ((xa, (-1.0, 0.0, 0.0)), (xb, (1.0, 0.0, 0.0))):
        _wall_face(bm, [pt(x, s, z) for s, z in profile], direction)

    for k in range(steps):
        z = z0 + (k + 1) * riser
        _wall_face(  # tread / проступь
            bm,
            [pt(xa, k * tread, z), pt(xb, k * tread, z), pt(xb, (k + 1) * tread, z), pt(xa, (k + 1) * tread, z)],
            (0.0, 0.0, 1.0),
        )
        z_low = z0 + k * riser
        _wall_face(  # riser (the first one rises from the floor) / подступенок (первый поднимается от пола)
            bm,
            [pt(xa, k * tread, z_low), pt(xb, k * tread, z_low), pt(xb, k * tread, z), pt(xa, k * tread, z)],
            towards_low,
        )
    _wall_face(  # sloped underside / скошенный низ
        bm,
        [pt(xa, 0.0, z0 - thick), pt(xb, 0.0, z0 - thick), pt(xb, length, z_top - thick), pt(xa, length, z_top - thick)],
        (0.0, 0.0, -1.0),
    )


def _stair_levels(props, storeys):
    """Z of the bottom of every flight pair, from the ground up to `storeys`.

    A normal storey is one level. A podium storey (several normal storeys tall)
    is `podium_levels` levels stacked, so the stair keeps a sensible step.

    Русский: Z низа каждой пары маршей, от земли до `storeys`. Обычный этаж
    это один ярус. Этаж стилобата (в несколько обычных высотой) это
    `podium_levels` ярусов друг над другом, поэтому шаг лестницы остаётся
    нормальным.
    """
    starts = []
    for k in range(1, storeys + 1):
        if k == 1 and props.podium:
            starts += [n * props.floor_height for n in range(props.podium_levels)]
        else:
            starts.append(slab_top(props, k - 1))
    return starts


def build_stairs(props, offset):
    """Fire stairs: two flights and a half landing per floor, up to `stairs_up_to`.

    `stairs_style`: FLIGHT = stepped concrete flights on inclined slabs (like a
    precast stair), BLOCKS = one box per step, stepping up and touching at the
    corners. Steps are about STAIR_RISER_TARGET high in both styles.

    A stair fills one whole module (the slabs have a hole there on every floor),
    edge to edge, so the landing touches the corner columns. On floors above
    `stairs_up_to` the hole stays but the stair is not built yet. The flights
    start at the module side that touches the rest of the building, so the stair
    arrives on a slab. Each storey: flight one goes up to the half landing along
    the left, flight two comes back along the right and reaches the next floor.

    Русский: Пожарные лестницы: на каждом этаже два марша и половинная
    площадка, до этажа `stairs_up_to`. `stairs_style`: FLIGHT это
    ступенчатые бетонные марши на наклонных плитах (как сборная лестница),
    BLOCKS это по боксу на ступень лесенкой, касающиеся углами. Ступени
    высотой около STAIR_RISER_TARGET в обоих стилях. Лестница занимает
    модуль целиком (в плитах там дыра на каждом этаже), от кромки до кромки,
    поэтому площадка касается угловых колонн. Выше `stairs_up_to` дыра
    остаётся, а лестница ещё не построена. Марши начинаются со стороны
    модуля, касающейся остального здания, чтобы лестница выходила на плиту.
    На каждом этаже: первый марш идёт вдоль левой стороны до половинной
    площадки, второй возвращается вдоль правой и выходит на следующий этаж.
    """
    size = props.module_size
    floor_h = props.floor_height
    footprint = footprint_cells(props)
    levels = min(props.stairs_up_to, props.floors)
    bm = bmesh.new()
    flight_len = size - STAIR_LANDING
    if levels < 1 or flight_len < 0.5:
        return bm

    flight_w = min(1.4, (size - 0.2) / 2)  # a small gap stays between the flights / между маршами остаётся небольшой зазор
    flight_style = props.stairs_style == "FLIGHT"
    landing_thick = STAIR_THICKNESS if flight_style else props.slab_thickness
    half = floor_h / 2
    steps = max(1, round(half / STAIR_RISER_TARGET))
    riser = half / steps
    tread = flight_len / steps
    for i, j in sorted(stair_cells(props)):
        xa = i * size
        xb = xa + size
        y0 = j * size
        # start from the side with a neighbour (normally -Y)
        # начинаем со стороны с соседом (обычно -Y)
        sign = stair_sign(footprint, i, j)
        origin = y0 if sign > 0 else y0 + size
        y_land = origin + sign * flight_len  # where the landing starts / где начинается площадка
        y_end = origin + sign * size  # the far side of the module / дальняя сторона модуля
        for z_start in _stair_levels(props, levels):
            z_mid = z_start + half
            if flight_style:
                _stair_flight_solid(bm, xa, xa + flight_w, origin, sign, z_start, steps, tread, riser)
                _stair_flight_solid(bm, xb - flight_w, xb, y_land, -sign, z_mid, steps, tread, riser)
            else:
                _stair_flight(bm, xa, xa + flight_w, origin, sign, z_start, steps, flight_len, half)
                _stair_flight(bm, xb - flight_w, xb, y_land, -sign, z_mid, steps, flight_len, half)
            _add_box(  # the half landing, as thick as the concrete under the steps / половинная площадка, той же толщины, что бетон под ступенями
                bm,
                (xa, min(y_land, y_end), z_mid - landing_thick),
                (xb, max(y_land, y_end), z_mid),
            )

    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)
    return bm


FORMWORK_TUBE_LOW = 0.07  # metres, the thick lower tube of a prop (square) / метры, толстая нижняя труба стойки (квадрат)
FORMWORK_TUBE_HIGH = 0.05  # metres, the thinner inner tube / метры, более тонкая внутренняя труба
FORMWORK_COLLAR = 0.1  # metres, the adjusting collar between the two / метры, регулировочная муфта между ними
FORMWORK_PLATE = 0.2  # metres, base and head plate (square) / метры, опорная и верхняя плита (квадрат)
FORMWORK_PLATE_T = 0.02
FORMWORK_BEARER_W = 0.1  # metres, the beam along the prop rows (rests on the heads) / метры, балка вдоль рядов стоек (лежит на головках)
FORMWORK_BEARER_H = 0.15
FORMWORK_JOIST_W = 0.08  # metres, the beams across it, right under the slab / метры, балки поперёк неё, прямо под плитой
FORMWORK_JOIST_H = 0.10
FORMWORK_JOIST_STEP = 0.75  # metres, about / метры, примерно
FORMWORK_LEG_W = 0.025  # metres, tripod leg / метры, раскос треноги
FORMWORK_LEG_HUB = 0.9  # metres, height of the tripod on the prop / метры, высота треноги на стойке
FORMWORK_LEG_REACH = 0.5  # metres, how far a tripod leg reaches along the floor / метры, как далеко раскос треноги достаёт по полу


def _add_bar(bm, start, end, side, thickness, height):
    """A thin bar from `start` to `end`, in any direction. Sides only (no end caps).

    The cross-section is `thickness` along `side` (a unit vector at right angles
    to the bar) and `height` across that. The 8 corners are shared by the faces.

    Русский: Тонкий брусок от `start` до `end` в любом направлении. Только
    боковые грани (без торцов). Сечение: `thickness` вдоль `side` (единичный
    вектор под прямым углом к бруску) и `height` поперёк. 8 углов общие для
    граней.
    """
    a = Vector(start)
    b = Vector(end)
    axis = (b - a).normalized()
    side = Vector(side).normalized()
    up = axis.cross(side).normalized()
    half_t = thickness / 2
    half_h = height / 2
    corners = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    ring_a = [bm.verts.new(tuple(a + side * sx * half_t + up * sy * half_h)) for sx, sy in corners]
    ring_b = [bm.verts.new(tuple(b + side * sx * half_t + up * sy * half_h)) for sx, sy in corners]
    for k in range(4):
        n = (k + 1) % 4
        outward = side * (corners[k][0] + corners[n][0]) + up * (corners[k][1] + corners[n][1])
        face = bm.faces.new([ring_a[k], ring_a[n], ring_b[n], ring_b[k]])
        face.normal_update()
        if face.normal.dot(outward) < 0:
            face.normal_flip()


def _add_strut(bm, start, end, width):
    """A thin square bar from `start` to `end`, in any direction. Sides only.

    Русский: Тонкий квадратный брусок от `start` до `end` в любом
    направлении. Только боковые грани.
    """
    axis = (Vector(end) - Vector(start)).normalized()
    side = axis.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1e-6:
        side = Vector((1.0, 0.0, 0.0))
    _add_bar(bm, start, end, side, width, width)


def build_formwork(props, offset, beams=False):
    """Formwork props: telescopic posts and timber beams under the top slabs.

    Under each of the top `formwork_levels` slabs every module (shafts and
    stairs excluded) gets a grid of props about `formwork_spacing` apart. A prop
    has a base plate, a thick lower tube, a collar, a thinner upper tube, a head
    plate and, with `formwork_tripods`, three legs on the floor. On the heads lie
    beams along X (one row per prop row), and on them a second layer of thinner
    beams across, right under the slab, as on a real site. At the outer edge of
    the building the beams stick out past the slab by a random length up to
    `formwork_overhang`. The grid is centred in the module, so props stay clear
    of the corner columns.

    The steel (props, plates, tripods) and the timber (both layers of beams) are
    separate objects, so the timber gets its own ID: `beams=False` builds the
    steel, `beams=True` the timber.

    Русский: Опалубка: телескопические стойки и деревянные балки под
    верхними плитами. Под каждой из верхних `formwork_levels` плит каждый
    модуль (кроме шахт и лестниц) получает сетку стоек с шагом около
    `formwork_spacing`. У стойки опорная плита, толстая нижняя труба, муфта,
    более тонкая верхняя труба, верхняя плита и, с `formwork_tripods`, три
    раскоса на полу. На головках лежат балки вдоль X (по одной на ряд
    стоек), а на них второй слой более тонких балок поперёк, прямо под
    плитой, как на настоящей стройке. На наружном краю здания балки торчат
    за плиту на случайную длину до `formwork_overhang`. Сетка по центру
    модуля, поэтому стойки не задевают угловые колонны. Сталь (стойки,
    плиты, треноги) и дерево (оба слоя балок) это отдельные объекты, чтобы у
    дерева был свой ID: `beams=False` строит сталь, `beams=True` дерево.
    """
    size = props.module_size
    floor_h = props.floor_height
    slab = props.slab_thickness
    footprint = footprint_cells(props)
    cells = footprint - shaft_cells(props) - stair_cells(props)
    count = max(1, round(size / props.formwork_spacing))
    pitch = size / count
    joists = max(1, round(size / FORMWORK_JOIST_STEP))
    leg_reach = min(FORMWORK_LEG_REACH, pitch / 2 - 0.05)
    low = FORMWORK_TUBE_LOW / 2
    high = FORMWORK_TUBE_HIGH / 2
    collar = FORMWORK_COLLAR / 2
    plate = FORMWORK_PLATE / 2
    holes = slab_holes(props)
    bm = bmesh.new()
    for level in range(props.floors - min(props.formwork_levels, props.floors) + 1, props.floors + 1):
        z_floor = slab_top(props, level - 1)  # top of the slab below (or the ground) / верх плиты ниже (или земли)
        z_under = slab_top(props, level) - slab  # underside of the slab above / низ плиты выше
        z_joist = z_under - FORMWORK_JOIST_H
        z_bearer = z_joist - FORMWORK_BEARER_H
        z_head = z_bearer - FORMWORK_PLATE_T
        z_base = z_floor + FORMWORK_PLATE_T
        if z_head - z_base < 0.5:
            continue
        z_split = z_base + 0.55 * (z_head - z_base)  # where the two tubes meet / где сходятся две трубы
        for i, j in sorted(cells):
            x0 = i * size
            y0 = j * size
            rng = random.Random(f"{props.random_seed}|formwork|{level}|{i}|{j}")

            def overhang():
                """A random length past the slab edge (drawn always, so the rest
                of the pattern never shifts when neighbours change)."""
                return rng.uniform(0.25, 1.0) * props.formwork_overhang

            for k in range(joists if beams else 0):  # the upper layer of beams, along Y / верхний слой балок, вдоль Y
                x = x0 + (k + 0.5) * size / joists
                past_lo = overhang()
                past_hi = overhang()
                if (i, j - 1) in footprint:  # a beam only sticks out past the building's edge / балка выступает только за край здания
                    past_lo = 0.0
                if (i, j + 1) in footprint:
                    past_hi = 0.0
                _add_box(
                    bm,
                    (x - FORMWORK_JOIST_W / 2, y0 - past_lo, z_joist),
                    (x + FORMWORK_JOIST_W / 2, y0 + size + past_hi, z_under),
                )
            for ky in range(count):
                y = y0 + (ky + 0.5) * pitch
                if beams:  # the beam along X on the heads / балка вдоль X на головках
                    past_lo = overhang()
                    past_hi = overhang()
                    if (i - 1, j) in footprint:
                        past_lo = 0.0
                    if (i + 1, j) in footprint:
                        past_hi = 0.0
                    _add_box(  # the beam along X on the heads / балка вдоль X на головках
                        bm,
                        (x0 - past_lo, y - FORMWORK_BEARER_W / 2, z_bearer),
                        (x0 + size + past_hi, y + FORMWORK_BEARER_W / 2, z_joist),
                    )
                for kx in range(0 if beams else count):
                    x = x0 + (kx + 0.5) * pitch
                    hole = holes.get((level - 1, (i, j)))  # no prop stands over a hole / стойка не стоит над отверстием
                    if hole is not None and _hole_blocks(hole, x, y, plate + 0.05):
                        continue
                    _add_box(bm, (x - plate, y - plate, z_floor), (x + plate, y + plate, z_base), bottom=False)
                    _add_box(bm, (x - low, y - low, z_base), (x + low, y + low, z_split), bottom=False)
                    _add_box(bm, (x - collar, y - collar, z_split), (x + collar, y + collar, z_split + 0.07))
                    _add_box(bm, (x - high, y - high, z_split + 0.07), (x + high, y + high, z_head), bottom=False)
                    _add_box(bm, (x - plate, y - plate, z_head), (x + plate, y + plate, z_bearer))
                    if props.formwork_tripods:
                        for angle in (90.0, 210.0, 330.0):
                            dx = math.cos(math.radians(angle))
                            dy = math.sin(math.radians(angle))
                            _add_strut(
                                bm,
                                (x, y, z_base + FORMWORK_LEG_HUB),
                                (x + dx * leg_reach, y + dy * leg_reach, z_base),
                                FORMWORK_LEG_W,
                            )
    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
    return bm


RAIL_BOARD_T = 0.03  # metres, plank thickness / метры, толщина доски
RAIL_BOARD_H = 0.15  # metres, plank height / метры, высота доски
RAIL_POST = 0.06  # metres, square post / метры, квадратная стойка
RAIL_OFFSET = 0.06  # metres, from the slab edge to the outer face of the planks / метры, от края плиты до наружной стороны досок


RAIL_BOARD_OVERLAP = 0.05  # metres, a board runs this far into the column at each end / метры, на столько доска заходит в колонну с каждого конца


def _add_railing(bm, props, i, j, di, dj, z, rng):
    """Edge protection on one side of slab module (i, j), standing on a slab at z.

    The side faces the neighbour at (di, dj). Between the corner columns there
    are a random number of horizontal boards (`railing_boards`) and of posts
    (`railing_posts`). Every board sits at a random height, with random gaps
    between the boards, and is tilted by a random angle up to `railing_tilt`
    either way. Posts are spread along the span with random gaps. The boards lie
    on the outer face of the posts. `rng` makes the variety repeat on Rebuild.

    Русский: Ограждение на одной стороне модуля плиты (i, j), стоящее на
    плите на высоте z. Сторона обращена к соседу (di, dj). Между угловыми
    колоннами случайное число горизонтальных досок (`railing_boards`) и
    стоек (`railing_posts`). Каждая доска на случайной высоте, со случайными
    промежутками между досками, и наклонена на случайный угол до
    `railing_tilt` в обе стороны. Стойки расставлены по пролёту со
    случайными промежутками. Доски лежат на наружной стороне стоек. `rng`
    делает разнообразие повторяемым при Rebuild.
    """
    size = props.module_size
    if dj != 0:  # the edge runs along X / кромка идёт вдоль X
        axis = "x"
        line = (j if dj < 0 else j + 1) * size
        start = i * size
        half = props.column_width / 2
        inward = 1 if dj < 0 else -1
    else:
        axis = "y"
        line = (i if di < 0 else i + 1) * size
        start = j * size
        half = props.column_depth / 2
        inward = 1 if di < 0 else -1
    a0 = start + half
    a1 = start + size - half
    length = a1 - a0
    if length <= 0.2:
        return

    def point(along, offset, height):
        if axis == "x":
            return (along, line + inward * offset, height)
        return (line + inward * offset, along, height)

    side = (0.0, inward, 0.0) if axis == "x" else (float(inward), 0.0, 0.0)
    height = props.railing_height

    # horizontal boards: random count, height, gap and tilt
    # горизонтальные доски: случайные число, высота, промежуток и наклон
    low, high = sorted(props.railing_boards)
    boards = rng.randint(low, high)
    band = height / boards
    reach = length + 2 * RAIL_BOARD_OVERLAP
    centre_offset = RAIL_OFFSET + RAIL_BOARD_T / 2
    for k in range(boards):
        angle = rng.uniform(-props.railing_tilt, props.railing_tilt)
        rise = math.tan(angle) * reach / 2  # how far each end moves from the middle / насколько каждый конец смещается от середины
        lowest = k * band + abs(rise)
        highest = (k + 1) * band - RAIL_BOARD_H - abs(rise)
        bottom = rng.uniform(lowest, max(lowest, highest))
        middle = z + bottom + RAIL_BOARD_H / 2
        _add_bar(
            bm,
            point(a0 - RAIL_BOARD_OVERLAP, centre_offset, middle - rise),
            point(a1 + RAIL_BOARD_OVERLAP, centre_offset, middle + rise),
            side,
            RAIL_BOARD_T,
            RAIL_BOARD_H,
        )

    def post_box(along, z_lo, z_hi):
        p_a = line + inward * (RAIL_OFFSET + RAIL_BOARD_T)
        p_b = line + inward * (RAIL_OFFSET + RAIL_BOARD_T + RAIL_POST)
        p_lo, p_hi = min(p_a, p_b), max(p_a, p_b)
        a_lo, a_hi = along - RAIL_POST / 2, along + RAIL_POST / 2
        if axis == "x":
            _add_box(bm, (a_lo, p_lo, z_lo), (a_hi, p_hi, z_hi), bottom=False)
        else:
            _add_box(bm, (p_lo, a_lo, z_lo), (p_hi, a_hi, z_hi), bottom=False)

    # vertical posts: random count, spread along the span with random gaps
    # вертикальные стойки: случайное число, расставлены по пролёту со случайными промежутками
    low, high = sorted(props.railing_posts)
    posts = rng.randint(low, high)
    band = length / posts
    for k in range(posts):
        post_box(a0 + (k + rng.uniform(0.2, 0.8)) * band, z, z + height)


def build_railings(props, offset):
    """Edge protection on the open edges of the slabs of the chosen floors.

    Open edges are the outer edge of the building and the edge of every stair
    hole (a shaft has walls, so it needs none). Where the stair of a floor
    arrives on the slab, the side of the hole it arrives at is left open, as long
    as the stair is built up to that floor.

    Русский: Ограждение на открытых краях плит выбранных этажей. Открытые
    края это наружный край здания и край каждого лестничного проёма (у шахты
    стены, ограждение ей не нужно). Там, где лестница этажа выходит на
    плиту, сторона проёма, куда она выходит, остаётся открытой, пока
    лестница построена до этого этажа.
    """
    footprint = footprint_cells(props)
    shafts = shaft_cells(props)
    stairs = stair_cells(props)
    cells = footprint - shafts - stairs
    floors, _ok = parse_floor_set(props.railing_floors, props.floors + 1)
    built_up_to = min(props.stairs_up_to, props.floors)

    edges = []  # (module, neighbour offset, is the stair's arrival side) / (модуль, смещение соседа, сторона выхода лестницы ли)
    for i, j in sorted(cells):
        for di, dj in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            neighbour = (i + di, j + dj)
            if neighbour in shafts or (neighbour in footprint and neighbour not in stairs):
                continue
            arrival = False
            if neighbour in stairs:
                sign = stair_sign(footprint, *neighbour)
                arrival = (i - neighbour[0], j - neighbour[1]) == (0, -sign)
            edges.append(((i, j), (di, dj), arrival))

    bm = bmesh.new()
    for slab in range(1, props.floors + 1):
        if slab + 1 not in floors:  # floor numbers: 1 = ground, slab k is floor k + 1 / номера этажей: 1 = земля, плита k это этаж k + 1
            continue
        for (i, j), (di, dj), arrival in edges:
            if arrival and slab <= built_up_to:
                continue
            rng = random.Random(f"{props.random_seed}|rail|{slab}|{i}|{j}|{di}|{dj}")
            _add_railing(bm, props, i, j, di, dj, slab_top(props, slab), rng)
    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
    return bm


LAMP_WIDTH = 0.1  # metres / метры
LAMP_HEIGHT = 0.06  # metres / метры
LAMP_MARGIN = 0.35  # metres from the module edge (columns, railings) / метры от края модуля (колонны, ограждения)


def build_lamps(props, offset):
    """Construction strip lamps: long thin boxes hung under the slabs.

    Every module of the selected floors (`lamp_floors`: the ceiling of storey k
    is slab k) gets at most one lamp with probability `lamp_factor` times the
    module's edge weight, so lamps gather round the edge of the building where
    they are seen. In a module on the outer edge the lamp runs parallel to that
    edge, a little way in from it; in the middle it can lie anywhere. A lamp has
    no top face (it is against the ceiling). The top slabs that have formwork get
    none, and no lamp hangs under a hole. Seeded per (floor, module).

    Русский: Строительные лампы: длинные тонкие боксы, подвешенные под
    плитами. Каждый модуль выбранных этажей (`lamp_floors`: потолок этажа k
    это плита k) получает не больше одной лампы с вероятностью `lamp_factor`
    на вес модуля, поэтому лампы собираются по краю здания, где их видно. В
    модуле на внешнем краю лампа идёт параллельно этому краю, чуть отступив
    от него; в середине может лежать где угодно. У лампы нет верхней грани
    (она у потолка). Под верхними плитами с опалубкой ламп нет, и ни одна не
    висит под отверстием. Зерно на (этаж, модуль).
    """
    size = props.module_size
    seed = props.random_seed
    footprint = footprint_cells(props)
    cells = sorted(footprint - shaft_cells(props) - stair_cells(props))
    weights = detail_weights(props)
    holes = slab_holes(props)
    low, high = sorted(props.lamp_length)
    floors, _ok = parse_floor_set(props.lamp_floors, props.floors)
    propped = set()
    if props.formwork:
        propped = set(range(props.floors - min(props.formwork_levels, props.floors) + 1, props.floors + 1))
    room = size - 2 * LAMP_MARGIN
    bm = bmesh.new()
    if room < 0.3:
        return bm
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for storey in sorted(floors):
        if storey in propped:
            continue
        z_under = slab_top(props, storey) - props.slab_thickness
        for i, j in cells:
            if _roll(seed, "lamp", storey, i, j) >= props.lamp_factor * weights[(i, j)]:
                continue
            rng = random.Random(f"{seed}|lamp-shape|{storey}|{i}|{j}")
            length = min(rng.uniform(low, high), room)
            x0 = i * size
            y0 = j * size
            outer = [(dx, dy) for dx, dy in sides if (i + dx, j + dy) not in footprint]
            if outer:  # parallel to the outer edge, a little way in from it / параллельно наружному краю, чуть отступив от него
                dx, dy = rng.choice(outer)
                gap = rng.uniform(LAMP_MARGIN, LAMP_MARGIN + 0.45)
                along = rng.uniform(LAMP_MARGIN, LAMP_MARGIN + room - length)
                if dy:
                    y = y0 + (gap if dy < 0 else size - gap)
                    rect = (x0 + along, y - LAMP_WIDTH / 2, x0 + along + length, y + LAMP_WIDTH / 2)
                else:
                    x = x0 + (gap if dx < 0 else size - gap)
                    rect = (x - LAMP_WIDTH / 2, y0 + along, x + LAMP_WIDTH / 2, y0 + along + length)
            else:
                along = rng.uniform(LAMP_MARGIN, LAMP_MARGIN + room - length)
                across = rng.uniform(LAMP_MARGIN, size - LAMP_MARGIN - LAMP_WIDTH)
                if rng.random() < 0.5:
                    rect = (x0 + along, y0 + across, x0 + along + length, y0 + across + LAMP_WIDTH)
                else:
                    rect = (x0 + across, y0 + along, x0 + across + LAMP_WIDTH, y0 + along + length)
            hole = holes.get((storey, (i, j)))
            if hole is not None and _rects_overlap(hole, rect):
                continue
            _add_box(bm, (rect[0], rect[1], z_under - LAMP_HEIGHT), (rect[2], rect[3], z_under), top=False)
    for v in bm.verts:
        v.co.x += offset[0]
        v.co.y += offset[1]
    return bm


def _get_collection(context):
    """The collection that holds the building (created if it is missing).

    Русский: Коллекция со зданием (создаётся, если её нет).
    """
    coll = bpy.data.collections.get(COLLECTION_NAME)
    if coll is None:
        coll = bpy.data.collections.new(COLLECTION_NAME)
    if coll.name not in context.scene.collection.children:
        context.scene.collection.children.link(coll)
    return coll


def _put_mesh(coll, name, bm):
    """Put the bmesh into the object `name` (created if missing) and return the object.

    Русский: Кладёт bmesh в объект `name` (создаётся, если его нет) и
    возвращает объект.
    """
    obj = coll.objects.get(name)
    if obj is None:
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        coll.objects.link(obj)
    mesh = obj.data
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    return obj


def _remove_object(coll, name):
    """Remove the object `name` and its mesh.

    Русский: Удаляет объект `name` и его меш.
    """
    obj = coll.objects.get(name)
    if obj is None:
        return
    mesh = obj.data
    bpy.data.objects.remove(obj)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _box_uvs(mesh, cell=None, cut_z=None):
    """Box projection in world metres: 1 UV unit = 1 m, the same for every object.

    Each polygon is projected along its dominant normal axis. Signs are chosen
    so a texture reads the same way (not mirrored, "up" stays up) when seen from
    outside. Objects sit at the origin with no rotation or scale, so object
    space equals world space.

    With `cell` (the module size) every polygon is shifted by its own amount per
    module, so the UVs of neighbouring modules do not meet: each module becomes
    its own island. A whole slab is then not one 36 m island but many identical
    3 m ones, which stack on each other and take almost no space.

    With `cut_z` (a height in metres) the polygons above each multiple of it get
    their own shift too, so a very tall island (a column over many floors) is
    cut into pieces of at most `cut_z` metres. A tall island would otherwise
    limit the scale of the whole tile.

    Returns (uvs, starts, totals, loop_verts): the flat UV list (u, v per loop)
    and the mesh arrays the UV island search needs.

    Русский: Box Projection в метрах мира: 1 UV-единица = 1 м, одинаково у
    всех объектов. Каждый полигон проецируется по главной оси его нормали.
    Знаки выбраны так, чтобы текстура читалась одинаково (не зеркалилась,
    «верх» оставался верхом) при взгляде снаружи. Объекты стоят в нуле без
    поворота и масштаба, поэтому пространство объекта равно мировому.
    С `cut_z` (высота в метрах) полигоны выше каждого кратного ей уровня тоже получают свой сдвиг, поэтому очень высокий островок (колонна на много этажей) режется на куски не выше `cut_z` метров. Иначе высокий островок ограничивал бы масштаб всего тайла.
    С `cell` (размер модуля) каждый полигон сдвигается на своё значение на каждый модуль, поэтому UV соседних модулей не стыкуются: каждый модуль становится отдельным островком. Тогда целая плита это не один островок 36 м, а много одинаковых по 3 м, которые ложатся друг на друга и почти не занимают места.
    Возвращает (uvs, starts, totals, loop_verts): плоский список UV (u, v на
    петлю) и массивы меша, нужные поиску островков UV.
    """
    n_polys = len(mesh.polygons)
    n_loops = len(mesh.loops)
    co = [0.0] * (3 * len(mesh.vertices))
    mesh.vertices.foreach_get("co", co)
    normals = [0.0] * (3 * n_polys)
    mesh.polygons.foreach_get("normal", normals)
    starts = [0] * n_polys
    totals = [0] * n_polys
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", totals)
    loop_verts = [0] * n_loops
    mesh.loops.foreach_get("vertex_index", loop_verts)

    uvs = [0.0] * (2 * n_loops)
    for p in range(n_polys):
        nx, ny, nz = normals[3 * p], normals[3 * p + 1], normals[3 * p + 2]
        ax, ay, az = abs(nx), abs(ny), abs(nz)
        shift = 0.0
        if cut_z:  # a different shift for every `cut_z` metres of height / свой сдвиг на каждые `cut_z` метров высоты
            zs = [co[3 * loop_verts[loop] + 2] for loop in range(starts[p], starts[p] + totals[p])]
            shift = 1.0e7 * math.floor(sum(zs) / len(zs) / cut_z)
        if cell:  # a different shift for every module: its UVs stay apart from the neighbours' / свой сдвиг на каждый модуль
            corners = [loop_verts[loop] for loop in range(starts[p], starts[p] + totals[p])]
            cx = sum(co[3 * v] for v in corners) / len(corners)
            cy = sum(co[3 * v + 1] for v in corners) / len(corners)
            shift += 1000.0 * (math.floor(cx / cell) + 100.0 * math.floor(cy / cell))
        for loop in range(starts[p], starts[p] + totals[p]):
            v = loop_verts[loop]
            x, y, z = co[3 * v], co[3 * v + 1], co[3 * v + 2]
            if az >= ax and az >= ay:
                u, w = (x, y) if nz > 0 else (x, -y)
            elif ax >= ay:
                u, w = (y, z) if nx > 0 else (-y, z)
            else:
                u, w = (-x, z) if ny > 0 else (x, z)
            uvs[2 * loop] = u + shift
            uvs[2 * loop + 1] = w + shift
    return uvs, starts, totals, loop_verts


def _find_islands(uvs, starts, totals, loop_verts, digits=4):
    """Group polygons into UV islands: lists of loop indices.

    Two polygons are in one island when they share an edge and have the same UV
    at both ends of it (compared to `digits` decimals).

    Русский: Группирует полигоны в островки UV: списки индексов петель. Два
    полигона в одном островке, если у них общее ребро и одинаковые UV на
    обоих его концах (сравнение до `digits` знаков).
    """
    n_polys = len(starts)
    parent = list(range(n_polys))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    seen = {}
    for p in range(n_polys):
        first = starts[p]
        count = totals[p]
        for k in range(count):
            la = first + k
            lb = first + (k + 1) % count
            va, vb = loop_verts[la], loop_verts[lb]
            ua = (round(uvs[2 * la], digits), round(uvs[2 * la + 1], digits))
            ub = (round(uvs[2 * lb], digits), round(uvs[2 * lb + 1], digits))
            key = (va, ua, vb, ub) if va < vb else (vb, ub, va, ua)
            other = seen.setdefault(key, p)
            if other != p:
                ra, rb = find(p), find(other)
                if ra != rb:
                    parent[ra] = rb
    groups = {}
    for p in range(n_polys):
        groups.setdefault(find(p), []).extend(range(starts[p], starts[p] + totals[p]))
    return list(groups.values())


# UV / material groups. Each group gets its own band of the UV tile and its own
# colour in the ID mask: (name, ID colour, the objects in it).
# Группы UV и материалов. У каждой группы своя полоса UV-тайла и свой цвет в ID-маске: (имя, цвет
# ID, объекты в ней).
GROUPS = (
    ("Concrete", (1.0, 0.0, 0.0), (FLOORS_NAME, COLUMNS_NAME, WALLS_NAME, SHAFTS_NAME, STAIRS_NAME)),
    ("Debris", (0.0, 1.0, 0.0), (DEBRIS_NAME,)),
    ("Formwork", (0.0, 0.0, 1.0), (FORMWORK_NAME,)),
    ("Railings", (1.0, 1.0, 0.0), (RAILINGS_NAME,)),
    ("Beams", (0.0, 1.0, 1.0), (FORMWORK_BEAMS_NAME,)),  # the timber beams of the formwork / деревянные балки опалубки
    ("Lamps", (1.0, 0.0, 1.0), (LAMPS_NAME,)),
    # The slabs are one object but three groups: chosen per face, not per object / плиты один объект, но три группы: по грани, а не по объекту
    ("Floors", (1.0, 0.5, 0.0), ()),  # slab tops / верх плит (полы)
    ("Ceilings", (0.55, 0.0, 1.0), ()),  # slab undersides / низ плит (потолки)
)
GROUP_FLOORS = 6
GROUP_CEILINGS = 7
ID_BACKGROUND = (0.05, 0.05, 0.05)


def slab_face_group(normal_z):
    """Group of a slab face: tops are floors, undersides ceilings, edges concrete.

    Русский: Группа грани плиты: верх это полы, низ потолки, торцы бетон.
    """
    if normal_z > 0.9:
        return GROUP_FLOORS
    if normal_z < -0.9:
        return GROUP_CEILINGS
    return 0


def group_of(name):
    """Index into GROUPS of the object called `name`.

    Русский: Индекс в GROUPS объекта с именем `name`.
    """
    for index, (_name, _color, names) in enumerate(GROUPS):
        if name in names:
            return index
    return 0


def _skyline_layout(sizes, scale, gap):
    """Pack rectangles into a strip one tile wide with the skyline method.

    `sizes` are (width, height) in metres. The rectangles are taken tallest
    first. Each one goes to the lowest place along the skyline (the top edge
    of what is already placed) where it fits, the leftmost on a tie, so it
    fills the gaps next to lower neighbours instead of leaving them empty as
    rows of equal height would. Returns (positions, height) with the lower-left
    corners in tile units, in the order of `sizes`, or None if a rectangle is
    wider than the strip.

    Русский: Упаковывает прямоугольники в полосу шириной в один тайл методом
    «силуэта» (skyline). `sizes` это (ширина, высота) в метрах. Прямоугольники
    берутся от самых высоких. Каждый ставится в самое низкое место вдоль
    силуэта (верхней кромки уже уложенного), куда он влезает, при равенстве
    левее, поэтому он заполняет пустоты рядом с более низкими соседями, а не
    оставляет их, как ряды одинаковой высоты. Возвращает (позиции, высота) с
    левыми нижними углами в единицах тайла, в порядке `sizes`, или None, если
    какой-то прямоугольник шире полосы.
    """
    limit = 1.0 - gap
    padded = []
    for w, h in sizes:
        pw = w * scale + gap
        ph = h * scale + gap
        if pw > limit:
            return None
        padded.append((pw, ph))
    order = sorted(range(len(padded)), key=lambda i: (-padded[i][1], i))

    sky = [[0.0, 0.0, limit]]  # segments [x, height of the top edge, width] / сегменты [x, высота кромки, ширина]
    positions = [None] * len(padded)
    top = 0.0
    for index in order:
        pw, ph = padded[index]
        best_x = best_y = None
        for i in range(len(sky)):
            x = sky[i][0]
            if x + pw > limit + 1e-9:
                break
            y = sky[i][1]
            covered = sky[i][2]
            j = i
            while covered < pw - 1e-9:  # the highest segment under the rectangle / самый высокий сегмент под ним
                j += 1
                y = max(y, sky[j][1])
                covered += sky[j][2]
            if best_y is None or y < best_y - 1e-9 or (abs(y - best_y) <= 1e-9 and x < best_x):
                best_x, best_y = x, y
        positions[index] = (best_x + gap / 2, best_y + gap / 2)
        top = max(top, best_y + ph)

        end = best_x + pw  # the new skyline: cut the covered part, add the rectangle's top / новый силуэт
        cut = []
        for sx, sy, sw in sky:
            se = sx + sw
            if se <= best_x + 1e-9 or sx >= end - 1e-9:
                cut.append([sx, sy, sw])
                continue
            if sx < best_x - 1e-9:
                cut.append([sx, sy, best_x - sx])
            if se > end + 1e-9:
                cut.append([end, sy, se - end])
        cut.append([best_x, best_y + ph, pw])
        cut.sort(key=lambda segment: segment[0])
        sky = []
        for segment in cut:  # join neighbours of the same height / склеить соседей одной высоты
            if sky and abs(sky[-1][1] - segment[1]) < 1e-9 and abs(sky[-1][0] + sky[-1][2] - segment[0]) < 1e-9:
                sky[-1][2] += segment[2]
            else:
                sky.append(segment)
    return positions, top


def _gap(margin, count):
    """Gap between rectangles: `margin`, but never so big that `count` of them cannot fit.

    Русский: Зазор между прямоугольниками: `margin`, но не больше, чем позволяет уместить `count` штук.
    """
    return min(margin, 0.45 / math.sqrt(max(count, 1)))


def _pack_bands(bands, margin):
    """Pack groups of rectangles into the unit tile, one band per group.

    `bands` is a list of size lists (see _skyline_layout). The
    bands are stacked from the bottom, each as high as its rectangles need, and
    all share ONE uniform scale: the largest one that still fits the tile (found
    by bisection). The gap between rectangles is `margin`, but never so big that
    thousands of small rectangles could not fit.

    Returns (scale, positions, ranges): positions[band][i] is the lower-left
    corner of rectangle i of that band, ranges[band] its (v start, v end).

    Русский: Упаковывает группы прямоугольников в единичный тайл, по полосе
    на группу. `bands` это список списков размеров (см. _skyline_layout). Полосы стопкой снизу, каждая такой высоты,
    какая нужна её прямоугольникам, и все с ОДНИМ равномерным масштабом:
    самым крупным, при котором всё ещё влезает в тайл (подбирается делением
    пополам). Зазор между прямоугольниками `margin`, но не больше, чем
    позволяет уместить тысячи мелких. Возвращает (масштаб, позиции,
    диапазоны): positions[полоса][i] это левый нижний угол прямоугольника i
    этой полосы, ranges[полоса] её (v начало, v конец).
    """
    gap = _gap(margin, sum(len(sizes) for sizes in bands))

    def layout(scale):
        positions = []
        ranges = []
        y0 = 0.0
        for sizes in bands:
            result = _skyline_layout(sizes, scale, gap)
            if result is None:
                return None
            placed, height = result
            positions.append([(x, y + y0) for x, y in placed])
            ranges.append((y0, y0 + height))
            y0 += height
        if y0 > 1.0:
            return None
        return positions, ranges

    biggest = max(max(w, h) for sizes in bands for w, h in sizes)
    total_area = sum(w * h for sizes in bands for w, h in sizes)
    # the scale can be no bigger than the widest rectangle allows or than the total area allows
    # масштаб не больше, чем позволяет самый большой прямоугольник и суммарная площадь
    low, high = 0.0, min((1.0 - gap) / biggest, 1.0 / math.sqrt(total_area))
    best = layout(high)
    if best is not None:
        return (high, *best)
    best = None
    for _ in range(40):
        if high - low <= 2e-4 * high:  # a 0.02% finer scale would not show / точнее 0.02% масштаба не видно
            break
        mid = (low + high) / 2
        result = layout(mid)
        if result is None:
            high = mid
        else:
            low, best = mid, result
    if best is None:
        best = ([[(gap / 2, gap / 2)] * len(sizes) for sizes in bands], [(0.0, 0.0)] * len(bands))
    return (low, *best)


def _group_similar(sizes, tolerance):
    """Group islands of a similar size, like Stack Similar in TechArt Tools.

    `sizes` is a list of (width, height). An island joins the first group whose
    first island (the anchor) has both width and height within `tolerance`
    (a fraction: 0.02 = 2%) of its own; otherwise it starts a new group. The
    order of `sizes` decides the anchors, so list the biggest first. Returns a
    list of groups, each a list of indices into `sizes`. Anchors are looked up
    in buckets of the size, so thousands of islands stay fast.

    Русский: Группирует островки похожего размера, как Stack Similar в
    TechArt Tools. `sizes` это список (ширина, высота). Островок входит в
    первую группу, у чьего первого островка (якоря) и ширина, и высота в
    пределах `tolerance` (доля: 0.02 = 2%) от его собственных; иначе он
    начинает новую группу. Порядок `sizes` задаёт якоря, поэтому самые
    большие первыми. Возвращает список групп, каждая это список индексов в
    `sizes`. Якоря ищутся по корзинам размера, поэтому тысячи островков
    обрабатываются быстро.
    """
    if not tolerance or tolerance <= 0.0:
        exact = {}
        for n, (w, h) in enumerate(sizes):
            exact.setdefault((round(w, 5), round(h, 5)), []).append(n)
        return list(exact.values())
    step = -math.log(1.0 - min(tolerance, 0.99))  # sizes within `tolerance` are at most a bucket apart / размеры в пределах `tolerance` отличаются не больше чем на корзину
    groups = []
    anchors = []  # (width, height) of each group's anchor / (ширина, высота) якоря каждой группы
    buckets = {}
    for n, (w, h) in enumerate(sizes):
        bw = math.floor(math.log(w) / step)
        bh = math.floor(math.log(h) / step)
        found = None
        for dw in (-1, 0, 1):
            for dh in (-1, 0, 1):
                for g in buckets.get((bw + dw, bh + dh), ()):
                    aw, ah = anchors[g]
                    if abs(w - aw) <= max(w, aw) * tolerance and abs(h - ah) <= max(h, ah) * tolerance:
                        if found is None or g < found:
                            found = g
        if found is None:
            groups.append([n])
            anchors.append((w, h))
            buckets.setdefault((bw, bh), []).append(len(groups) - 1)
        else:
            groups[found].append(n)
    return groups


def unwrap(context, objs, margin, similarity=None, grouped=True, split_cell=None, cut_height=None):
    """Box projection, then pack the islands of all objects into one 0-1 tile.

    All objects share ONE UV layout (one texture for the whole building). The
    packing is done here, in Python, instead of with the Pack Islands operator:
    that operator depends on the editor state (UV selection, sync mode, the
    active area) and did nothing in some sessions. Islands keep their
    orientation (no rotation) and one uniform scale, so the texel density is the
    same everywhere.

    Islands of a similar size (`similarity`, for example 0.02 = 2%, like Range in
    TechArt Tools) are placed on top of each other, centred, floor on floor and
    door on door, which saves most of the space. `similarity=None` gives every
    island its own place. With `grouped`, only islands of the same group (GROUPS)
    are stacked, so the ID mask can colour every place with its group. All groups
    are packed together in one skyline, with no per-group bands, so no space is
    lost between groups. The slabs are one object but three groups: tops go to
    Floors, undersides to Ceilings, edges stay in Concrete (see slab_face_group).
    With `cut_height` (metres) the UVs of tall objects (columns over many floors)
    are cut every `cut_height` metres, so no island limits the scale of the tile.
    With `split_cell` (the module size times the cut size) the slabs are cut into
    pieces of that size, one island each (see _box_uvs).

    Returns [(group, x0, y0, x1, y1)]: the cell of every stack in tile units, for
    the ID mask.

    Русский: Box Projection, затем упаковка островков всех объектов в один
    тайл 0-1. Все объекты делят ОДНУ UV-раскладку (одна текстура на всё
    здание). Упаковка сделана здесь, на Python, а не оператором Pack
    Islands: оператор зависит от состояния редактора (выбор UV, режим sync,
    активная область) и в некоторых сессиях ничего не делал. Островки
    сохраняют ориентацию (без поворота) и один равномерный масштаб, поэтому
    плотность текселей везде одинакова. Островки похожего размера
    (`similarity`, например 0.02 = 2%, как Range в TechArt Tools) кладутся
    друг на друга по центру, пол на пол и дверь на дверь, что экономит почти
    всё место. `similarity=None` даёт каждому островку своё место. С
    `grouped` друг на друга ложатся только островки одной группы (GROUPS),
    поэтому ID-маска может покрасить каждое место в цвет своей группы. Все
    группы упаковываются вместе одним силуэтом, без полос на группу, поэтому
    место между группами не теряется. Плиты это один объект, но три группы:
    верх идёт в Floors, низ в Ceilings, торцы остаются в Concrete (см.
    slab_face_group). С `split_cell` (размер модуля на размер куска) плиты
    режутся на куски этого размера, по островку на кусок (см. _box_uvs).
    С `cut_height` (метры) UV высоких объектов (колонн на много этажей) режутся через каждые `cut_height` метров, чтобы ни один островок не ограничивал масштаб тайла. : ячейку каждой стопки в единицах
    тайла, для ID-маски.
    """
    layouts = []
    rects = []  # (object index, loops, min u, min v, width, height, group) / (индекс объекта, петли, мин u, мин v, ширина, высота, группа)
    for index, obj in enumerate(objs):
        cell = split_cell if obj.name == FLOORS_NAME else None  # only the slabs are cut per module / по модулям режутся только плиты
        cut_z = None if obj.name == FLOORS_NAME else cut_height  # tall islands are cut by height / высокие островки режутся по высоте
        uvs, starts, totals, loop_verts = _box_uvs(obj.data, cell, cut_z)
        group = group_of(obj.name) if grouped else 0
        normals = None
        if grouped and obj.name == FLOORS_NAME:  # the slabs go to the group of their face / плиты идут в группу своей грани
            normals = [0.0] * (3 * len(starts))
            obj.data.polygons.foreach_get("normal", normals)
        pieces = []  # (loops, group)
        for loops in _find_islands(uvs, starts, totals, loop_verts):
            if normals is None:
                pieces.append((loops, group))
                continue
            # A top and an edge face can touch in UV by chance and be found as one island:
            # split such an island by group, so every face keeps its own colour.
            # Верх и торец могут случайно совпасть в UV и найтись одним островком: делим его по группам.
            parts = {}
            for loop in loops:
                polygon = bisect.bisect_right(starts, loop) - 1
                parts.setdefault(slab_face_group(normals[3 * polygon + 2]), []).append(loop)
            pieces += [(part, part_group) for part_group, part in parts.items()]
        for loops, island_group in pieces:
            us = [uvs[2 * loop] for loop in loops]
            vs = [uvs[2 * loop + 1] for loop in loops]
            low_u, low_v = min(us), min(vs)
            rects.append((index, loops, low_u, low_v, max(max(us) - low_u, 1e-6), max(max(vs) - low_v, 1e-6), island_group))
        layouts.append(uvs)
    if not rects:
        return []

    by_group = {}
    for n, rect in enumerate(rects):
        by_group.setdefault(rect[6], []).append(n)

    stacks = []  # (group, island numbers): islands of one group that share one place / (группа, номера островков)
    for group in sorted(by_group):
        numbers = sorted(by_group[group], key=lambda n: -(rects[n][4] * rects[n][5]))
        if similarity is None:  # no stacking: every island has its own place / без стопок: у каждого островка своё место
            found_stacks = [[n] for n in numbers]
        else:
            sized = [(rects[n][4], rects[n][5]) for n in numbers]
            found_stacks = [[numbers[k] for k in found] for found in _group_similar(sized, similarity)]
        stacks += [(group, stack) for stack in found_stacks]
    stacks.sort(key=lambda item: -max(rects[n][5] for n in item[1]))
    sizes = [(max(rects[n][4] for n in stack), max(rects[n][5] for n in stack)) for _group, stack in stacks]

    # ONE strip for all groups: no per-group bands, so no space is lost between groups
    # ОДНА полоса на все группы: без полос на группу, поэтому место между группами не теряется
    scale, positions, _ranges = _pack_bands([sizes], margin)
    gap = _gap(margin, len(sizes))
    id_rects = []
    for (group, stack), (stack_w, stack_h), (x, y) in zip(stacks, sizes, positions[0]):
        centre_x = x + stack_w * scale / 2
        centre_y = y + stack_h * scale / 2
        for n in stack:
            index, loops, low_u, low_v, width, height, _group = rects[n]
            mid_u = low_u + width / 2
            mid_v = low_v + height / 2
            uvs = layouts[index]
            for loop in loops:
                uvs[2 * loop] = (uvs[2 * loop] - mid_u) * scale + centre_x
                uvs[2 * loop + 1] = (uvs[2 * loop + 1] - mid_v) * scale + centre_y
        id_rects.append((
            group,
            max(x - gap / 2, 0.0), max(y - gap / 2, 0.0),
            min(x + stack_w * scale + gap / 2, 1.0), min(y + stack_h * scale + gap / 2, 1.0),
        ))
    for obj, uvs in zip(objs, layouts):
        obj.data.uv_layers.active.data.foreach_set("uv", uvs)
        obj.data.update()
    return id_rects


def _group_material(group):
    """The flat-colour material of a group (created once, colour = its ID colour).

    Русский: Материал плоского цвета группы (создаётся один раз, цвет = её
    ID-цвет).
    """
    name, color, _names = GROUPS[group]
    material = bpy.data.materials.get(f"CB_{name}")
    if material is None:
        material = bpy.data.materials.new(f"CB_{name}")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    material.diffuse_color = (*color, 1.0)
    return material


def _make_id_image(size, id_rects):
    """The ID mask: the cell of every stack of islands filled with its group colour.

    `id_rects` is [(group, x0, y0, x1, y1)] in tile units, from unwrap. The rest
    is the dark background.

    Русский: ID-маска: ячейка каждой стопки островков залита цветом её группы.
    `id_rects` это [(группа, x0, y0, x1, y1)] в единицах тайла, из unwrap.
    Остальное тёмный фон.
    """
    import numpy as np

    image = bpy.data.images.get(ID_IMAGE_NAME)
    if image is not None and tuple(image.size) != (size, size):
        bpy.data.images.remove(image)
        image = None
    if image is None:
        image = bpy.data.images.new(ID_IMAGE_NAME, size, size, alpha=False)
    pixels = np.empty((size, size, 4), dtype=np.float32)
    pixels[:, :, :3] = ID_BACKGROUND
    pixels[:, :, 3] = 1.0
    for group, x0, y0, x1, y1 in id_rects:
        pixels[int(round(y0 * size)):int(round(y1 * size)), int(round(x0 * size)):int(round(x1 * size)), :3] = GROUPS[group][1]
    image.pixels.foreach_set(pixels.ravel())
    image.update()
    return image


def assign_ids(props, objs, id_rects, materials=True):
    """Build the ID mask image and, unless `materials` is off, give every object
    the material of its group. The slab object gets three materials (concrete,
    floors, ceilings), picked per face.

    Русский: Строит картинку ID-маски и, если не выключено `materials`,
    ставит каждому объекту материал его группы. Объект плит получает три
    материала (бетон, полы, потолки), выбираемых по грани.
    """
    if materials:
        for obj in objs:
            mesh = obj.data
            mesh.materials.clear()
            if obj.name != FLOORS_NAME:
                mesh.materials.append(_group_material(group_of(obj.name)))
                continue
            # the slabs: three materials, picked per face / плиты: три материала, по грани
            for group in (0, GROUP_FLOORS, GROUP_CEILINGS):
                mesh.materials.append(_group_material(group))
            normals = [0.0] * (3 * len(mesh.polygons))
            mesh.polygons.foreach_get("normal", normals)
            slots = {0: 0, GROUP_FLOORS: 1, GROUP_CEILINGS: 2}
            mesh.polygons.foreach_set("material_index", [slots[slab_face_group(normals[3 * p + 2])] for p in range(len(mesh.polygons))])
    _make_id_image(props.id_mask_size, id_rects)


def building_material(use_mask):
    """The one material of the single mesh: the ID mask as base colour.

    Русский: Единственный материал одного меша: ID-маска как базовый цвет.
    """
    material = bpy.data.materials.get("CB_Building")
    if material is None:
        material = bpy.data.materials.new("CB_Building")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    texture = nodes.get("CB_ID_Image")
    image = bpy.data.images.get(ID_IMAGE_NAME) if use_mask else None
    if image is not None:
        if texture is None:
            texture = nodes.new("ShaderNodeTexImage")
            texture.name = "CB_ID_Image"
        texture.image = image
        texture.interpolation = "Closest"
        if bsdf is not None:
            links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        if texture is not None:
            nodes.remove(texture)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
    return material


def join_objects(coll, objs, name):
    """Merge the meshes of `objs` into one new object called `name`.

    Done on the mesh data (vertices, loops, polygons, UVs, smooth flags), not
    with the Join operator, which depends on the editor state. The UV layout of
    the parts is kept as it is. The parts themselves are not removed here.

    Русский: Склеивает меши `objs` в один новый объект с именем `name`.
    Делается над данными меша (вершины, петли, полигоны, UV, флаги
    сглаживания), а не оператором Join, который зависит от состояния
    редактора. UV-раскладка частей сохраняется как есть. Сами части здесь не
    удаляются.
    """
    if coll.objects.get(name) is not None:
        _remove_object(coll, name)
    coords = []
    loop_verts = []
    starts = []
    totals = []
    smooth = []
    uvs = []
    vert_offset = 0
    loop_offset = 0
    for obj in objs:
        mesh = obj.data
        n_verts, n_loops, n_polys = len(mesh.vertices), len(mesh.loops), len(mesh.polygons)
        co = [0.0] * (3 * n_verts)
        mesh.vertices.foreach_get("co", co)
        lv = [0] * n_loops
        mesh.loops.foreach_get("vertex_index", lv)
        ps = [0] * n_polys
        mesh.polygons.foreach_get("loop_start", ps)
        pt = [0] * n_polys
        mesh.polygons.foreach_get("loop_total", pt)
        sm = [False] * n_polys
        mesh.polygons.foreach_get("use_smooth", sm)
        uv = [0.0] * (2 * n_loops)
        mesh.uv_layers.active.data.foreach_get("uv", uv)
        coords += co
        loop_verts += [v + vert_offset for v in lv]
        starts += [s + loop_offset for s in ps]
        totals += pt
        smooth += sm
        uvs += uv
        vert_offset += n_verts
        loop_offset += n_loops

    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(vert_offset)
    mesh.vertices.foreach_set("co", coords)
    mesh.loops.add(loop_offset)
    mesh.loops.foreach_set("vertex_index", loop_verts)
    mesh.polygons.add(len(starts))
    mesh.polygons.foreach_set("loop_start", starts)
    mesh.polygons.foreach_set("loop_total", totals)
    mesh.polygons.foreach_set("use_smooth", smooth)
    mesh.update(calc_edges=True)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.active.data.foreach_set("uv", uvs)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def rebuild(context, props):
    """(Re)create the building. Returns the object list (one object with `single_mesh`).

    Русский: (Пере)создаёт здание. Возвращает список объектов (один объект с
    `single_mesh`).
    """
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    if props.center_xy:
        offset = (
            -props.modules_x * props.module_size / 2,
            -props.modules_y * props.module_size / 2,
        )
    else:
        offset = (0.0, 0.0)

    coll = _get_collection(context)
    objs = [
        _put_mesh(coll, FLOORS_NAME, build_floors(props, offset)),
        _put_mesh(coll, COLUMNS_NAME, build_columns(props, offset)),
    ]
    optional = (
        (WALLS_NAME, props.walls, build_walls),
        (SHAFTS_NAME, props.shafts, build_shafts),
        (STAIRS_NAME, props.stairs, build_stairs),
        (FORMWORK_NAME, props.formwork, build_formwork),
        (FORMWORK_BEAMS_NAME, props.formwork, lambda p, o: build_formwork(p, o, beams=True)),
        (RAILINGS_NAME, props.railings, build_railings),
        (DEBRIS_NAME, props.debris, build_debris),
        (LAMPS_NAME, props.lamps, build_lamps),
    )
    for name, enabled, build in optional:
        bm = build(props, offset) if enabled else None
        if bm is not None and bm.faces:
            objs.append(_put_mesh(coll, name, bm))
        else:
            if bm is not None:
                bm.free()
            _remove_object(coll, name)

    id_rects = unwrap(
        context, objs, props.uv_margin,
        props.uv_similarity if props.uv_overlap else None,
        props.uv_groups,
        props.module_size * props.uv_split_size if props.uv_split_slabs else None,
        props.uv_column_cut or None,
    )
    has_mask = props.id_mask and props.uv_groups
    if has_mask:
        assign_ids(props, objs, id_rects, materials=not props.single_mesh)
    if props.single_mesh:  # one mesh, one material: easier to texture / один меш, один материал: удобнее текстурить
        building = join_objects(coll, objs, BUILDING_NAME)
        for name in [obj.name for obj in objs]:
            _remove_object(coll, name)
        building.data.materials.append(building_material(has_mask))
        objs = [building]
    else:
        _remove_object(coll, BUILDING_NAME)

    for obj in objs:
        obj.select_set(True)
    context.view_layer.objects.active = objs[0]
    return objs
