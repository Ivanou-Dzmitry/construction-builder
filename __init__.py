"""ConstructionBuilder: a generator of a building under construction (slabs, columns, walls, shafts,
stairs, formwork, railings, lamps, debris), with UVs, an ID mask and FBX export.

Русский: Генератор строящегося здания (плиты, колонны, стены, шахты, лестницы, опалубка, ограждения,
лампы, мусор) с UV, ID-маской и экспортом в FBX.
"""

from . import operators

modules = (operators,)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
