"""Properties, operators and the 3D Viewport panel for ConstructionBuilder.

Русский: Свойства, операторы и панель в 3D Viewport для ConstructionBuilder.
"""

import math
import os
import subprocess
import sys
import tomllib

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)

from . import builder, translations


def _iface(text):
    """Interface text in the language Blender is set to (Russian: translations.py).

    Русский: Текст интерфейса на языке, выбранном в Blender (русский:
    translations.py).
    """
    return bpy.app.translations.pgettext_iface(text)


def _rpt(text):
    """A report message in the language Blender is set to.

    Русский: Сообщение отчёта на языке, выбранном в Blender.
    """
    return bpy.app.translations.pgettext_rpt(text)


def _read_version():
    """Single source of truth: the `version` field of blender_manifest.toml.

    Русский: Единый источник версии: поле `version` в blender_manifest.toml.
    """
    path = os.path.join(os.path.dirname(__file__), "blender_manifest.toml")
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "?"


VERSION = _read_version()


class CB_Props(bpy.types.PropertyGroup):
    """All building parameters, stored in the scene as `scene.construction_builder`.

    Русский: Все параметры здания, хранятся в сцене как
    `scene.construction_builder`.
    """
    modules_x: IntProperty(
        name="Modules X",
        description="Number of floor modules along X (the building width)",
        default=4,
        min=1,
        soft_max=50,
    )
    modules_y: IntProperty(
        name="Modules Y",
        description="Number of floor modules along Y (the building length)",
        default=3,
        min=1,
        soft_max=50,
    )
    floors: IntProperty(
        name="Floors",
        description="Number of floors (storeys): every one has a slab on top",
        default=5,
        min=1,
        soft_max=100,
    )
    floor_height: FloatProperty(
        name="Floor Height",
        description="Distance between two neighbouring slabs, in metres",
        default=3.0,
        min=0.5,
        unit="LENGTH",
    )
    module_size: FloatProperty(
        name="Module Size",
        description="Side of one square floor module and the column grid step",
        default=3.0,
        min=0.5,
        unit="LENGTH",
    )
    ground_slab: BoolProperty(
        name="Ground Slab",
        description="A slab at ground level, so the building stands on the "
        "ground. Its top is at Z = 0 and it has its thickness, but no bottom "
        "face (that is in the ground). Solid under shafts and stairs",
        default=True,
    )
    slab_thickness: FloatProperty(
        name="Slab Thickness",
        description="Thickness of the floor slabs",
        default=0.3,
        min=0.01,
        unit="LENGTH",
    )
    column_width: FloatProperty(
        name="Column Width",
        description="Column size along X",
        default=0.4,
        min=0.01,
        unit="LENGTH",
    )
    column_depth: FloatProperty(
        name="Column Depth",
        description="Column size along Y",
        default=0.4,
        min=0.01,
        unit="LENGTH",
    )
    column_extension: FloatProperty(
        name="Column Top Extension",
        description="How far the columns stick out above the top slab",
        default=1.0,
        min=0.0,
        unit="LENGTH",
    )
    column_foot: FloatProperty(
        name="Foot Depth",
        description="How far the columns go below the ground (Z = 0), so they do "
        "not hang above it. The default is deeper than the ground slab. 0 = the "
        "columns start at ground level",
        default=0.5,
        min=0.0,
        unit="LENGTH",
    )
    column_height_variation: FloatProperty(
        name="Height Variation",
        description="Each column gets a random extra 0..this height above the "
        "top slab, so the column tops are not level",
        default=0.5,
        min=0.0,
        unit="LENGTH",
    )
    rebar: BoolProperty(
        name="Rebar",
        description="Add a 3x3 group of thin boxes (rebar) sticking out of "
        "every column top",
        default=True,
    )
    rebar_height: FloatProperty(
        name="Rebar Height",
        description="How far the rebar sticks out above the column top",
        default=0.8,
        min=0.01,
        unit="LENGTH",
    )
    rebar_height_variation: FloatProperty(
        name="Height Random",
        description="Every rod gets its own height: Rebar Height plus or minus "
        "this value (random, depends on Seed)",
        default=0.1,
        min=0.0,
        unit="LENGTH",
    )
    rebar_size: FloatProperty(
        name="Rebar Size",
        description="Side of one square rebar rod",
        default=0.04,
        min=0.005,
        unit="LENGTH",
    )
    random_seed: IntProperty(
        name="Seed",
        description="Seed for the random column heights, rebar, walls, doors, railings, debris, lamps and holes",
        default=1,
        min=0,
    )
    walls: BoolProperty(
        name="Walls",
        description="Build interior walls between the columns (the outer "
        "contour stays an open frame)",
        default=True,
    )
    wall_floors: StringProperty(
        name="Wall Floors",
        description="Floors that get walls, e.g. '1-3, 5' or 'all'. Floor 1 is "
        "the one between the ground and the first slab",
        default="1-2",
    )
    wall_thickness: FloatProperty(
        name="Wall Thickness",
        description="Wall thickness, centred on the grid line",
        default=0.2,
        min=0.01,
        unit="LENGTH",
    )
    wall_chance: FloatProperty(
        name="Wall Chance",
        description="Share of the inner module edges that get a wall (random, "
        "depends on Seed). The same on every floor, so rooms stack. 1 = walls "
        "everywhere",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    door_chance: FloatProperty(
        name="Door Chance",
        description="Share of walls that get a door opening (random, depends "
        "on Seed). The rest are solid",
        default=0.4,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    door_width: FloatProperty(
        name="Door Width",
        description="Door opening width, centred in the wall",
        default=1.2,
        min=0.3,
        unit="LENGTH",
    )
    door_height: FloatProperty(
        name="Door Height",
        description="Door opening height from the floor",
        default=2.1,
        min=0.3,
        unit="LENGTH",
    )
    shafts: BoolProperty(
        name="Elevator Shafts",
        description="Build elevator shafts: a hollow tube around each listed "
        "module, ground to above the roof. The slabs get a hole there",
        default=True,
    )
    shaft_count: IntProperty(
        name="Count",
        description="Number of elevator shafts. They stand in a row along X in "
        "the middle of the building, centred",
        default=1,
        min=1,
        max=10,
    )
    shaft_padding: FloatProperty(
        name="Padding",
        description="Clear gap between neighbouring shafts, in metres (rounded "
        "to whole modules): 3, 9, 18 ...",
        default=9.0,
        min=0.0,
        unit="LENGTH",
    )
    shaft_cells: StringProperty(
        name="Custom Modules",
        description="Optional. Modules with a shaft as X,Y pairs counted from "
        "1, separated by ';', e.g. '2,2; 8,2'. When filled in, Count and "
        "Padding are ignored. Leave empty for automatic placement",
        default="",
    )
    shaft_thickness: FloatProperty(
        name="Shaft Wall",
        description="Shaft wall thickness, centred on the module edge",
        default=0.3,
        min=0.01,
        unit="LENGTH",
    )
    shaft_extension: FloatProperty(
        name="Top Block",
        description="Height of the shaft's top block above the roof: its last "
        "floor, standing on the top slab. It gets a door like the other floors "
        "when it is at least 1.5 m high. 0 = the shaft ends at the roof",
        default=3.0,
        min=0.0,
        unit="LENGTH",
    )
    shaft_door_side: EnumProperty(
        name="Door Side",
        description="Side of the shaft that gets a door on every floor",
        items=[
            ("-Y", "-Y (front)", "Door on the side facing -Y"),
            ("+Y", "+Y (back)", "Door on the side facing +Y"),
            ("-X", "-X (left)", "Door on the side facing -X"),
            ("+X", "+X (right)", "Door on the side facing +X"),
        ],
        default="-Y",
    )
    shaft_columns: EnumProperty(
        name="Corner Columns",
        description="What happens to the four columns at the corners of a shaft, "
        "which would end up inside the walls of its top block",
        items=[
            ("TRIM", "Trimmed", "The columns end at the roof slab, without rebar: the shaft rises above them"),
            ("REMOVE", "Removed", "No columns at the shaft corners: the shaft walls carry the floors"),
            ("FULL", "Full", "Same as every other column (they end up inside the top block, with the rebar sticking out)"),
        ],
        default="TRIM",
    )
    shaft_clear_radius: IntProperty(
        name="Clear Walls",
        description="No interior walls within this many modules around a shaft, "
        "so the shaft stays visible. 0 = only the shaft's own module",
        default=1,
        min=0,
        max=10,
    )
    debris: BoolProperty(
        name="Debris",
        description="Scatter boxes (bricks, pallets...) on random slabs, so the "
        "frame looks lived-in. No bottom faces",
        default=True,
    )
    debris_floors: StringProperty(
        name="Floors",
        description="Floors with debris, e.g. '1-3, 5' or 'all'. Same numbering "
        "as Wall Floors: 1 is the ground, the highest number is the roof",
        default="all",
    )
    debris_factor: FloatProperty(
        name="Factor",
        description="Share of the modules (on the chosen floors) that get "
        "a box. Random, depends on Seed. 0 = none, 1 = every module",
        default=0.2,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    debris_height: FloatVectorProperty(
        name="Height",
        description="Random box height range, metres (min, max)",
        size=2,
        default=(0.5, 2.0),
        min=0.05,
        unit="LENGTH",
    )
    debris_length: FloatVectorProperty(
        name="Length",
        description="Random box length range, metres (min, max)",
        size=2,
        default=(1.0, 2.0),
        min=0.05,
        unit="LENGTH",
    )
    debris_width: FloatVectorProperty(
        name="Width",
        description="Random box width range, metres (min, max)",
        size=2,
        default=(0.4, 1.0),
        min=0.05,
        unit="LENGTH",
    )
    shape: EnumProperty(
        name="Shape",
        description="Footprint of the building, seen from above",
        items=[
            ("RECT", "Rectangle", "A plain rectangle"),
            ("L", "L-shape", "Top bar and a left leg: a block is cut from the bottom-right corner"),
            ("U", "U-shape", "Top bar and two legs: a block is cut from the middle of the bottom side"),
        ],
        default="RECT",
    )
    shape_cut_x: IntProperty(
        name="Cut Width",
        description="Width of the cut-out block, in modules along X",
        default=2,
        min=1,
        soft_max=20,
    )
    shape_cut_y: IntProperty(
        name="Cut Depth",
        description="Depth of the cut-out block, in modules along Y. It always "
        "leaves at least one row for the top bar",
        default=2,
        min=1,
        soft_max=20,
    )
    stairs: BoolProperty(
        name="Fire Stairs",
        description="Fire stairs: a hole through every slab with a two-flight "
        "stair in it, built up to the chosen floor",
        default=True,
    )
    stairs_up_to: IntProperty(
        name="Built Up To Floor",
        description="The stair is built from the ground up to this floor. Above "
        "it only the hole in the slab remains. 0 = holes only",
        default=3,
        min=0,
        soft_max=100,
    )
    stairs_style: EnumProperty(
        name="Style",
        description="How the flights look",
        items=[
            ("FLIGHT", "Concrete Flight", "Stepped flight on an inclined concrete slab, with landings, like a precast stair"),
            ("BLOCKS", "Blocks", "A few big boxes stepping up, touching at the corners"),
        ],
        default="FLIGHT",
    )
    stairs_position: EnumProperty(
        name="Position",
        description="Where the stairs stand",
        items=[
            ("CENTER", "Center", "One stair in the middle of the building"),
            ("EDGE", "Edge", "One stair at the -X end of the building"),
            ("ENDS", "Both Ends", "A stair at each end of the building along X"),
        ],
        default="CENTER",
    )
    formwork: BoolProperty(
        name="Formwork Props",
        description="Steel props and timber beams under the top slabs, as under "
        "a freshly poured slab",
        default=True,
    )
    formwork_levels: IntProperty(
        name="Top Slabs",
        description="How many of the top slabs are propped",
        default=2,
        min=1,
        soft_max=10,
    )
    formwork_overhang: FloatProperty(
        name="Overhang",
        description="At the outer edge of the building the timber beams stick "
        "out past the slab by a random length from a quarter of this value up to "
        "it. 0 = the beams end flush with the slab",
        default=0.4,
        min=0.0,
        unit="LENGTH",
    )
    formwork_tripods: BoolProperty(
        name="Tripods",
        description="Three legs on the floor around the foot of every prop, as "
        "on real props. Turn off for fewer polygons",
        default=True,
    )
    formwork_jitter: FloatProperty(
        name="Randomness",
        description="Every prop is moved by a random distance up to this value, "
        "and every row of props with its beam too, so they do not stand in a "
        "perfect grid. Props stay clear of the corner columns. 0 = a perfect grid",
        default=0.4,
        min=0.0,
        soft_max=1.0,
        unit="LENGTH",
    )
    formwork_spacing: FloatProperty(
        name="Spacing",
        description="Distance between props, metres (rounded so a whole number "
        "fits in a module)",
        default=1.5,
        min=0.5,
        unit="LENGTH",
    )
    railings: BoolProperty(
        name="Railings",
        description="Edge protection (posts and three planks) on the open slab "
        "edges: the outer edge and the edges of the stair holes",
        default=True,
    )
    railing_floors: StringProperty(
        name="Floors",
        description="Floors with railings, e.g. '3-6' or 'all'. Same numbering as "
        "Wall Floors: 1 is the ground, the highest number is the roof",
        default="all",
    )
    railing_boards: IntVectorProperty(
        name="Boards",
        description="Every railing span gets a random number of horizontal "
        "boards in this range (min, max)",
        size=2,
        default=(1, 3),
        min=1,
        max=8,
    )
    railing_posts: IntVectorProperty(
        name="Posts",
        description="Every railing span gets a random number of vertical posts "
        "in this range (min, max)",
        size=2,
        default=(1, 3),
        min=1,
        max=8,
    )
    railing_tilt: FloatProperty(
        name="Tilt",
        description="Every board is tilted by a random angle between minus and "
        "plus this value",
        default=math.radians(5.0),
        min=0.0,
        max=math.radians(30.0),
        subtype="ANGLE",
    )
    railing_height: FloatProperty(
        name="Height",
        description="Railing height above the slab",
        default=1.1,
        min=0.4,
        unit="LENGTH",
    )
    podium: BoolProperty(
        name="Podium",
        description="A podium (stylobate): the first storey is several normal "
        "storeys tall. It keeps the shafts and stairs but has no partitions; "
        "walls and railings start from floor 2 (debris stays on every floor)",
        default=False,
    )
    podium_levels: IntProperty(
        name="Podium Height",
        description="How many normal storeys tall the first storey is",
        default=2,
        min=2,
        max=6,
    )
    unfinished: BoolProperty(
        name="Unfinished Part",
        description="One side of the building is not finished yet: it has fewer "
        "storeys than the rest, so it has no upper slabs, walls, stairs and "
        "props. Its columns stand with the rebar sticking out",
        default=False,
    )
    unfinished_side: EnumProperty(
        name="Side",
        description="Which side of the building is lower",
        items=[
            ("PX", "+X (Right)", "The right end of the building"),
            ("NX", "-X (Left)", "The left end of the building"),
            ("PY", "+Y (Back)", "The back of the building"),
            ("NY", "-Y (Front)", "The front of the building"),
        ],
        default="PX",
    )
    unfinished_modules: IntProperty(
        name="Width",
        description="How many module rows on that side are lower. At least one "
        "row always keeps the full height",
        default=3,
        min=1,
        soft_max=20,
    )
    unfinished_floors: IntProperty(
        name="Missing Floors",
        description="How many storeys that part lacks. At least one storey always "
        "stays",
        default=2,
        min=1,
        soft_max=20,
    )
    edge_bias: FloatProperty(
        name="Edge Bias",
        description="Random details (lamps, holes, debris) gather near the outer "
        "edge of the building, where they are seen. The chance in the deepest "
        "module is this much lower than at the edge: 0 = even, 1 = none in the middle",
        default=0.7,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    lamps: BoolProperty(
        name="Lamps",
        description="Construction strip lamps hung under the slabs, mostly near "
        "the outer edge of the building",
        default=True,
    )
    lamp_floors: StringProperty(
        name="Floors",
        description="Floors whose ceiling gets lamps, e.g. '2-5' or 'all'. Floor k "
        "is storey k: its lamps hang under slab k",
        default="all",
    )
    lamp_factor: FloatProperty(
        name="Factor",
        description="Share of the modules (on the chosen floors) that get a "
        "lamp, before the edge bias. Random, depends on Seed",
        default=0.3,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    lamp_length: FloatVectorProperty(
        name="Length",
        description="Random lamp length range, metres (min, max)",
        size=2,
        default=(0.8, 1.6),
        min=0.2,
        unit="LENGTH",
    )
    slab_holes: BoolProperty(
        name="Slab Holes",
        description="Random square holes in some slabs, for pipes and such, "
        "mostly near the outer edge of the building",
        default=True,
    )
    hole_factor: FloatProperty(
        name="Factor",
        description="Share of the slab modules that get a hole, before the edge "
        "bias. Random, depends on Seed",
        default=0.08,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    hole_size: FloatVectorProperty(
        name="Size",
        description="Random side of a square hole, metres (min, max)",
        size=2,
        default=(0.5, 1.0),
        min=0.1,
        unit="LENGTH",
    )
    center_xy: BoolProperty(
        name="Center on Origin",
        description="Centre the footprint on the world origin instead of "
        "starting its corner there",
        default=False,
    )
    uv_margin: FloatProperty(
        name="UV Margin",
        description="Gap between packed UV islands",
        default=0.005,
        min=0.0,
        max=0.2,
        precision=3,
    )
    uv_groups: BoolProperty(
        name="Group by Material",
        description="Split the UV islands into groups: concrete, floors, ceilings, "
        "debris, formwork, railings, beams, lamps. Islands of different groups "
        "never share space, so a mask can select a group by its colour",
        default=True,
    )
    id_mask: BoolProperty(
        name="ID Mask",
        description="Make a colour ID mask image (one colour per group, filling "
        "the UV places of its islands) and give every object the flat-colour material of its "
        "group. Saved next to the FBX when you export",
        default=True,
    )
    id_mask_size: IntProperty(
        name="Mask Size",
        description="Size of the ID mask image in pixels",
        default=2048,
        min=64,
        max=8192,
    )
    uv_split_slabs: BoolProperty(
        name="Split Slabs",
        description="Cut the UVs of the slabs into pieces (see Cut Size) instead of "
        "one huge island per floor. The identical pieces stack on each other, so "
        "the slabs take little space and the rest of the building gets a bigger "
        "scale. The slab texture then repeats every piece",
        default=True,
    )
    uv_split_size: IntProperty(
        name="Cut Size",
        description="Size of a slab piece in modules: 3 = 3 x 3 modules (9 x 9 m "
        "with 3 m modules). Smaller pieces save more space but repeat the "
        "texture more often",
        default=3,
        min=1,
        soft_max=10,
    )
    uv_column_cut: FloatProperty(
        name="Cut Height",
        description="Cut the UVs of tall objects (columns over many floors) every "
        "this many metres (the columns get an edge loop there). A very tall island "
        "would limit the scale of the whole tile. A building lower than this is "
        "not changed. 0 = do not cut",
        default=30.0,
        min=0.0,
        soft_max=60.0,
        precision=1,
        subtype="DISTANCE",
    )
    uv_overlap: BoolProperty(
        name="Overlap Similar",
        description="Put UV islands of a similar size on top of each other "
        "(floor on floor, door on door...) to save space in the tile. Turn off "
        "to give every island its own place",
        default=True,
    )
    uv_similarity: FloatProperty(
        name="Similarity",
        description="How close in size two islands must be to share a place: "
        "their width and height may differ by this fraction (0.02 = 2%, the "
        "same as Range in TechArt Tools)",
        default=0.02,
        min=0.0,
        max=0.5,
        subtype="FACTOR",
    )
    single_mesh: BoolProperty(
        name="Single Mesh",
        description="Bake the whole building into ONE mesh (CB_Building) with one "
        "material and one UV layout, which is easier to texture, for example in "
        "Substance Painter. The ID mask PNG still tells the groups apart",
        default=False,
    )
    export_one_material: BoolProperty(
        name="One Material",
        description="On export every object gets the single material CB_Building "
        "(the ID mask as base colour), so the FBX has ONE material and one "
        "texture set, for example in Substance Painter. The coloured group "
        "materials come back in Blender afterwards. The ID mask PNG still tells "
        "the groups apart",
        default=True,
    )
    export_dir: StringProperty(
        name="Folder",
        description="FBX export folder. Empty = a 'ConstructionBuilder' folder "
        "next to the .blend file (or in Documents if the file is not saved)",
        subtype="DIR_PATH",
        default="",
    )
    auto_name: BoolProperty(
        name="Auto Name",
        description="Rebuild writes the file name from the building into File: c, "
        "floors, modules X-Y, shape (R, L or U), for example c10_8-8_L. You can "
        "still edit it. Turn off to keep your own name",
        default=True,
    )
    file_name: StringProperty(
        name="File",
        description="FBX file name",
        default="ConstructionBuilder",
    )


def export_folder(props):
    """The folder the FBX goes to: the Folder field, or `ConstructionBuilder` next to the .blend.

    Русский: Папка, куда идёт FBX: поле Folder или папка
    `ConstructionBuilder` рядом с .blend-файлом.
    """
    if props.export_dir:
        return bpy.path.abspath(props.export_dir)
    if bpy.data.filepath:
        base = os.path.dirname(bpy.data.filepath)
    else:
        base = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(base, "ConstructionBuilder")


def auto_file_name(props):
    """The file name made from the building: c<floors>_<modules X>-<modules Y>_<shape>.

    The shape letter is R (rectangle), L or U. For example `c10_8-8_L`.

    Русский: Имя файла, собранное из здания: c<этажи>_<модули X>-<модули Y>_<форма>.
    Буква формы: R (прямоугольник), L или U. Например `c10_8-8_L`.
    """
    letter = {"RECT": "R", "L": "L", "U": "U"}[props.shape]
    return f"c{props.floors}_{props.modules_x}-{props.modules_y}_{letter}"


def export_path(props):
    """Full path of the FBX file (the File field, `.fbx` added if missing).

    Русский: Полный путь к файлу FBX (поле File, `.fbx` добавляется, если
    его нет).
    """
    name = props.file_name.strip() or "ConstructionBuilder"
    if not name.lower().endswith(".fbx"):
        name += ".fbx"
    return os.path.join(export_folder(props), name)


def _built_objects():
    """The building's objects that exist in the scene now.

    Русский: Объекты здания, которые сейчас есть в сцене.
    """
    names = (
        builder.FLOORS_NAME,
        builder.COLUMNS_NAME,
        builder.WALLS_NAME,
        builder.SHAFTS_NAME,
        builder.STAIRS_NAME,
        builder.FORMWORK_NAME,
        builder.FORMWORK_BEAMS_NAME,
        builder.RAILINGS_NAME,
        builder.DEBRIS_NAME,
        builder.LAMPS_NAME,
        builder.BUILDING_NAME,
    )
    objs = [bpy.data.objects.get(n) for n in names]
    return [o for o in objs if o is not None]


class CB_OT_rebuild(bpy.types.Operator):
    """Delete the previous result and build floors and columns again from the
    current parameters, then box-project and pack the UVs

    Русский: Удалить прежний результат и построить здание заново по текущим
    параметрам, затем сделать Box Projection и упаковать UV.
    """

    bl_idname = "construction_builder.rebuild"
    bl_label = "Rebuild"
    bl_description = (
        "Delete the previous result and build the building again from the current parameters, "
        "then box-project and pack the UVs"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.construction_builder
        objs = builder.rebuild(context, props)
        if props.auto_name:  # the name follows the building on every Rebuild / имя следует за зданием при каждом Rebuild
            props.file_name = auto_file_name(props)
        polys = ", ".join(f"{o.name}: {len(o.data.polygons)}" for o in objs)
        self.report({"INFO"}, f"{_rpt('Built')} {polys} {_rpt('polygons')}")
        return {"FINISHED"}


class CB_OT_export_fbx(bpy.types.Operator):
    """Export the whole building to an FBX file (and the ID mask as a PNG next to it)

    Русский: Экспортировать всё здание в FBX (и ID-маску в PNG рядом).
    """

    bl_idname = "construction_builder.export_fbx"
    bl_label = "Export FBX"
    bl_description = "Export the whole building to an FBX file (and the ID mask as a PNG next to it)"

    def execute(self, context):
        props = context.scene.construction_builder
        objs = _built_objects()
        if not objs:
            self.report({"ERROR"}, _rpt("Nothing to export. Press Rebuild first"))
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in context.view_layer.objects:
            obj.select_set(False)
        for obj in objs:
            obj.select_set(True)
        context.view_layer.objects.active = objs[0]

        path = export_path(props)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # One material on export: Substance makes a texture set per material, and
        # the groups are already told apart by the ID mask. The group materials are
        # put back afterwards, so the colours stay in Blender.
        # Один материал при экспорте: Substance делает texture set на каждый материал, а группы и
        # так различаются ID-маской. Материалы групп потом возвращаются, так что цвета в Blender
        # остаются.
        saved = []
        if props.export_one_material:
            single = builder.building_material(props.id_mask and props.uv_groups)
            for obj in objs:
                mesh = obj.data
                indices = [0] * len(mesh.polygons)
                mesh.polygons.foreach_get("material_index", indices)
                saved.append((obj, list(mesh.materials), indices))
                mesh.materials.clear()
                mesh.materials.append(single)
                mesh.polygons.foreach_set("material_index", [0] * len(indices))
        try:
            bpy.ops.export_scene.fbx(
                filepath=path,
                use_selection=True,
                object_types={"MESH"},
                add_leaf_bones=False,
                mesh_smooth_type="FACE",
            )
        finally:
            for obj, materials, indices in saved:
                mesh = obj.data
                mesh.materials.clear()
                for material in materials:
                    mesh.materials.append(material)
                mesh.polygons.foreach_set("material_index", indices)
        image = bpy.data.images.get(builder.ID_IMAGE_NAME)
        if image is not None and props.id_mask and props.uv_groups:
            id_path = os.path.splitext(path)[0] + "_ID.png"
            image.filepath_raw = id_path
            image.file_format = "PNG"
            image.save()
            self.report({"INFO"}, f"{_rpt('Exported')} {path} {_rpt('and')} {id_path}")
        else:
            self.report({"INFO"}, f"{_rpt('Exported')} {path}")
        return {"FINISHED"}


class CB_OT_open_folder(bpy.types.Operator):
    """Open the FBX export folder in the file explorer

    Русский: Открыть папку экспорта FBX в проводнике.
    """

    bl_idname = "construction_builder.open_folder"
    bl_label = "Open Folder"
    bl_description = "Open the FBX export folder in the file explorer"

    def execute(self, context):
        folder = export_folder(context.scene.construction_builder)
        os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
        return {"FINISHED"}


def _pair(layout, props, label, first, second, first_index=-1, second_index=-1):
    """A label and two input fields on ONE row, e.g. Cut (Width/Depth).

    Русский: Подпись и два поля ввода в ОДНОЙ строке, например Cut
    (Width/Depth).
    """
    split = layout.split(factor=0.4, align=True)
    split.use_property_split = False
    split.label(text=label)
    row = split.row(align=True)
    row.prop(props, first, text="", index=first_index)
    row.prop(props, second, text="", index=second_index)


class CB_PT_main(bpy.types.Panel):
    """The ConstructionBuilder panel in the 3D Viewport sidebar (N).

    Русский: Панель ConstructionBuilder в боковой панели 3D Viewport (N).
    """
    bl_label = "ConstructionBuilder"
    bl_idname = "CB_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ConstructionBuilder"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = context.scene.construction_builder

        layout.label(text=f"{_iface('Version')} {VERSION}")

        box = layout.box()
        box.label(text="Building", icon="MOD_BUILD")
        _pair(box, props, "Modules (X/Y)", "modules_x", "modules_y")
        box.prop(props, "floors")
        box.prop(props, "shape")
        if props.shape != "RECT":
            _pair(box, props, "Cut (Width/Depth)", "shape_cut_x", "shape_cut_y")
        box.prop(props, "floor_height")
        box.prop(props, "module_size")
        box.prop(props, "podium")
        sub = box.column()
        sub.active = props.podium
        sub.prop(props, "podium_levels")
        box.prop(props, "unfinished")
        sub = box.column(align=True)
        sub.active = props.unfinished
        sub.prop(props, "unfinished_side")
        sub.prop(props, "unfinished_modules")
        sub.prop(props, "unfinished_floors")
        box.prop(props, "edge_bias")
        box.prop(props, "center_xy")
        width = props.modules_x * props.module_size
        length = props.modules_y * props.module_size
        height = builder.total_height(props)
        count = len(builder.footprint_cells(props))
        box.label(
            text=f"{_iface('Size')}: {width:g} x {length:g} x {height:g} {_iface('m')}, {count} {_iface('modules')}"
        )

        box = layout.box()
        box.label(text="Slabs", icon="MESH_PLANE")
        box.prop(props, "slab_thickness")
        box.prop(props, "ground_slab")

        box = layout.box()
        box.label(text="Columns", icon="MESH_CUBE")
        _pair(box, props, "Size (Width/Depth)", "column_width", "column_depth")
        box.prop(props, "column_extension")
        box.prop(props, "column_foot")
        col = box.column(align=True)
        col.prop(props, "column_height_variation")
        col.prop(props, "random_seed")
        box.prop(props, "rebar")
        sub = box.column(align=True)
        sub.active = props.rebar
        sub.prop(props, "rebar_height")
        sub.prop(props, "rebar_height_variation")
        sub.prop(props, "rebar_size")

        box = layout.box()
        box.label(text="Walls", icon="MOD_WIREFRAME")
        box.prop(props, "walls")
        sub = box.column(align=True)
        sub.active = props.walls
        sub.prop(props, "wall_floors")
        _, floors_ok = builder.parse_floor_set(props.wall_floors, props.floors)
        if not floors_ok:
            sub.label(text="Wall Floors: use e.g. 1-3, 5 or all", icon="ERROR")
        sub.prop(props, "wall_thickness")
        sub.prop(props, "wall_chance")
        sub.prop(props, "door_chance")
        _pair(sub, props, "Door (Width/Height)", "door_width", "door_height")

        box = layout.box()
        box.label(text="Elevator Shafts", icon="MOD_SOLIDIFY")
        box.prop(props, "shafts")
        sub = box.column(align=True)
        sub.active = props.shafts
        row = sub.column(align=True)
        row.active = not props.shaft_cells.strip()
        row.prop(props, "shaft_count")
        row.prop(props, "shaft_padding")
        sub.prop(props, "shaft_cells")
        _, shafts_ok = builder.shaft_layout(props)
        if not shafts_ok:
            if props.shaft_cells.strip():
                sub.label(text="Custom Modules: X,Y from 1, e.g. 2,2; 8,2", icon="ERROR")
            else:
                sub.label(text="Shafts do not fit: lower Count or Padding", icon="ERROR")
        sub.prop(props, "shaft_thickness")
        sub.prop(props, "shaft_extension")
        sub.prop(props, "shaft_door_side")
        sub.prop(props, "shaft_columns")
        sub.prop(props, "shaft_clear_radius")

        box = layout.box()
        box.label(text="Fire Stairs", icon="SORT_ASC")
        box.prop(props, "stairs")
        sub = box.column(align=True)
        sub.active = props.stairs
        sub.prop(props, "stairs_style")
        sub.prop(props, "stairs_position")
        sub.prop(props, "stairs_up_to")

        box = layout.box()
        box.label(text="Formwork Props", icon="GRIP")
        box.prop(props, "formwork")
        sub = box.column(align=True)
        sub.active = props.formwork
        sub.prop(props, "formwork_levels")
        sub.prop(props, "formwork_spacing")
        sub.prop(props, "formwork_jitter")
        sub.prop(props, "formwork_overhang")
        sub.prop(props, "formwork_tripods")

        box = layout.box()
        box.label(text="Railings", icon="MOD_WIREFRAME")
        box.prop(props, "railings")
        sub = box.column(align=True)
        sub.active = props.railings
        sub.prop(props, "railing_floors")
        _, rail_floors_ok = builder.parse_floor_set(props.railing_floors, props.floors + 1)
        if not rail_floors_ok:
            sub.label(text="Railing Floors: use e.g. 3-6 or all", icon="ERROR")
        sub.prop(props, "railing_height")
        _pair(sub, props, "Boards (Min/Max)", "railing_boards", "railing_boards", 0, 1)
        _pair(sub, props, "Posts (Min/Max)", "railing_posts", "railing_posts", 0, 1)
        sub.prop(props, "railing_tilt")

        box = layout.box()
        box.label(text="Debris", icon="PARTICLES")
        box.prop(props, "debris")
        sub = box.column(align=True)
        sub.active = props.debris
        sub.prop(props, "debris_floors")
        _, debris_floors_ok = builder.parse_floor_set(props.debris_floors, props.floors + 1)
        if not debris_floors_ok:
            sub.label(text="Debris Floors: use e.g. 1-3, 5 or all", icon="ERROR")
        sub.prop(props, "debris_factor")
        for prop, label in (
            ("debris_height", "Height"),
            ("debris_length", "Length"),
            ("debris_width", "Width"),
        ):
            _pair(sub, props, f"{label} (Min/Max)", prop, prop, 0, 1)  # msgid, e.g. "Height (Min/Max)" / msgid, например "Height (Min/Max)"

        box = layout.box()
        box.label(text="Lamps", icon="LIGHT")
        box.prop(props, "lamps")
        sub = box.column(align=True)
        sub.active = props.lamps
        sub.prop(props, "lamp_floors")
        _, lamp_floors_ok = builder.parse_floor_set(props.lamp_floors, props.floors)
        if not lamp_floors_ok:
            sub.label(text="Lamp Floors: use e.g. 2-5 or all", icon="ERROR")
        sub.prop(props, "lamp_factor")
        _pair(sub, props, "Length (Min/Max)", "lamp_length", "lamp_length", 0, 1)

        box = layout.box()
        box.label(text="Slab Holes", icon="MESH_PLANE")
        box.prop(props, "slab_holes")
        sub = box.column(align=True)
        sub.active = props.slab_holes
        sub.prop(props, "hole_factor")
        _pair(sub, props, "Size (Min/Max)", "hole_size", "hole_size", 0, 1)

        box = layout.box()
        box.label(text="UV", icon="UV")
        box.prop(props, "uv_margin")
        box.prop(props, "uv_split_slabs")
        sub = box.column()
        sub.active = props.uv_split_slabs
        sub.prop(props, "uv_split_size")
        box.prop(props, "uv_column_cut")
        box.prop(props, "uv_groups")
        sub = box.column()
        sub.active = props.uv_groups
        sub.prop(props, "id_mask")
        sub.prop(props, "id_mask_size")
        box.prop(props, "uv_overlap")
        sub = box.column()
        sub.active = props.uv_overlap
        sub.prop(props, "uv_similarity")

        row = layout.row()
        row.scale_y = 1.6
        row.operator("construction_builder.rebuild", icon="FILE_REFRESH")

        box = layout.box()
        box.label(text="Export", icon="EXPORT")
        box.prop(props, "single_mesh")
        box.prop(props, "export_one_material")
        box.prop(props, "export_dir")
        box.prop(props, "file_name")
        box.prop(props, "auto_name")
        row = box.row(align=True)
        row.operator("construction_builder.export_fbx", icon="EXPORT")
        row.operator("construction_builder.open_folder", icon="FILE_FOLDER")


classes = (
    CB_Props,
    CB_OT_rebuild,
    CB_OT_export_fbx,
    CB_OT_open_folder,
    CB_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.construction_builder = PointerProperty(type=CB_Props)
    translations.register(CB_Props)


def unregister():
    translations.unregister()
    del bpy.types.Scene.construction_builder
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
