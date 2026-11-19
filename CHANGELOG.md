# Changelog / История изменений

The version is set in `blender_manifest.toml` (the `version` field) and shown at the top of the panel. Every code change bumps the version and adds an entry here. Every entry is written in English and in Russian.

Версия задаётся в `blender_manifest.toml` (поле `version`) и показывается вверху панели. Любое изменение кода поднимает версию, запись добавляется сюда. Каждая запись написана на английском и на русском.

## 0.28.0

**English**

* **No debris among the formwork props.** A box of debris used to stand right among the props and cross their tripods. Now, like the lamps, a module gets no debris on a floor where formwork props stand (the floors under the top `Top Slabs` slabs of its part, when `Formwork Props` is on). The other floors keep their debris. With the formwork off the debris did not change (bit-for-bit comparison on 3 configurations); with it on, the boxes in propped floors are gone (0 left in the test).

**Русский**

* **Мусора нет среди стоек опалубки.** Бокс мусора раньше мог стоять прямо среди стоек и пересекать их треноги. Теперь, как и у ламп, в модуле на этаже со стойками опалубки мусора нет (этажи под верхними `Top Slabs` плитами его части, когда включены `Formwork Props`). На остальных этажах мусор остаётся. При выключенной опалубке мусор не изменился (побитовое сравнение на 3 конфигурациях); при включённой боксов на этажах со стойками нет (в тесте осталось 0).

## 0.27.0

**English**

* **Save Config / Load Config** (the `Config` box above Export): **Save Config** writes all building parameters to a `.json` file named like the FBX (the `File` field, for example `c10_8-8_L.json`) in the export folder. **Load Config** opens a file browser, applies the file and rebuilds the building. Use it to keep a building or to give it to someone: the other person loads the file and gets exactly the same building (checked bit-for-bit on a U-shaped building with a podium and an unfinished part: the loaded geometry equals the saved one). The export folder is not saved, so a file from another computer does not touch your folder. A file from another version is loaded too: unknown names are skipped, missing ones stay default, and the result shows how many parameters were applied. A file that is not a config gives an error and changes nothing.

**Русский**

* **Save Config / Load Config** (блок `Config` над Export): **Save Config** записывает все параметры здания в файл `.json` с таким же именем, как у FBX (поле `File`, например `c10_8-8_L.json`), в папке экспорта. **Load Config** открывает выбор файла, применяет его и пересобирает здание. Так можно сохранить здание или отдать его кому-то: другой человек загружает файл и получает точно такое же здание (проверено побитово на П-образном здании со стилобатом и недостроенной частью: загруженная геометрия равна сохранённой). Папка экспорта не сохраняется, поэтому файл с другого компьютера вашу папку не трогает. Файл от другой версии тоже загружается: неизвестные имена пропускаются, отсутствующие остаются по умолчанию, а в сообщении видно, сколько параметров применено. Файл, который не конфиг, даёт ошибку и ничего не меняет.

## 0.26.0

**English**

* Debris is no longer removed from the podium floor: with `Podium` on, floor 1 gets its debris boxes like every other floor (before, debris started from floor 2 and the tall first storey was empty). Walls and railings still start from floor 2. Without a podium the geometry did not change (bit-for-bit comparison, 45 of 45 objects).

**Русский**

* Мусор больше не убирается с этажа стилобата: при включённом `Podium` на этаже 1 стоят боксы мусора, как на остальных этажах (раньше мусор начинался со 2-го этажа, и высокий первый этаж был пустым). Стены и ограждения по-прежнему начинаются со 2-го этажа. Без стилобата геометрия не изменилась (побитовое сравнение, 45 из 45 объектов).

## 0.25.0

**English**

* **Foot Depth** (`Foot Depth` in Columns, 0.5 m by default, 0 = as before): the columns used to start exactly at Z = 0, on top of the ground slab, and looked as if they hung above the ground. Now they go 0.5 m below the ground, through the ground slab (0.3 m thick by default). Columns still have no bottom face. Only the column meshes change (they are longer by `Foot Depth`); with `Foot Depth` = 0 the geometry did not change (bit-for-bit comparison, 45 of 45 objects).

**Русский**

* **Заглубление колонн** (`Foot Depth` в Columns, по умолчанию 0.5 м, 0 = как раньше): колонны начинались ровно на Z = 0, на плите на земле, и казалось, что они висят над землёй. Теперь они уходят на 0.5 м под землю, сквозь плиту на земле (по умолчанию толщиной 0.3 м). Нижней грани у колонн по-прежнему нет. Меняются только меши колонн (длиннее на `Foot Depth`); при `Foot Depth` = 0 геометрия не изменилась (побитовое сравнение, 45 из 45 объектов).

## 0.24.0

**English**

* **Randomness** (`Randomness` in Formwork Props, 0.4 m by default, 0 = perfect grid): the props no longer stand in a perfect grid. Every prop moves by a random distance up to this value, and every row of props moves with its timber beam, so the heads still lie under a beam. Props keep clear of the corner columns and stay inside the building (the tripod legs are counted, so the margin from the module edge is about 0.55 m). Seeded, so a Rebuild repeats it; the steel and the timber agree. With `Randomness` = 0 the geometry did not change (bit-for-bit comparison, 45 of 45 objects).

**Русский**

* **Разброс** (`Randomness` в Formwork Props, по умолчанию 0.4 м, 0 = идеальная сетка): стойки больше не стоят идеальной сеткой. Каждая стойка сдвигается на случайное расстояние до этого значения, а каждый ряд стоек сдвигается вместе со своей деревянной балкой, так что головки по-прежнему лежат под балкой. Стойки держатся подальше от угловых колонн и остаются внутри здания (раскосы треноги учитываются, поэтому отступ от края модуля около 0.55 м). С зерном, Rebuild повторяет результат; сталь и дерево согласованы. При `Randomness` = 0 геометрия не изменилась (побитовое сравнение, 45 из 45 объектов).

## 0.23.0

**English**

* **Auto Name** (`Auto Name`, on by default): every Rebuild writes the file name from the building into the `File` field: `c` + floors + `_` + modules X-Y + `_` + shape (R, L or U), for example `c10_8-8_L`. You can still edit the name by hand after a Rebuild; turn the checkbox off to keep your own name. The FBX and the ID mask (`<name>_ID.png`) get this name.

**Русский**

* **Авто-имя** (`Auto Name`, по умолчанию вкл.): каждый Rebuild записывает в поле `File` имя файла по зданию: `c` + этажи + `_` + модули X-Y + `_` + форма (R, L или U), например `c10_8-8_L`. После Rebuild имя можно поправить руками; чтобы сохранить своё имя, выключите галку. Это имя получают FBX и ID-маска (`<имя>_ID.png`).

## 0.22.0

**English**

* **Unfinished part** (`Unfinished Part`, `Side`, `Width`, `Missing Floors`; off by default): one side of the building is lower, as if the rest has already risen and this part is not built yet. `Side` is +X / -X / +Y / -Y, `Width` is how many module rows on that side are lower, `Missing Floors` is how many storeys they lack. It works for any shape: the legs of a U or the arm of an L can stay low while the bar goes up.
* The lower part has no upper slabs, walls, stairs, shafts, lamps, debris or railings above its own roof. Its columns stand at the roof height with the rebar sticking out, its formwork props are under its own top slabs, its railings fence its roof and every step edge of the taller part, its shafts and stairs end at its roof. A wall between a low and a tall module is as high as the low one.
* At least one storey and at least one module row always keep full height, whatever the numbers say.
* Without the option the geometry did not change (bit-for-bit comparison, 45 of 45 objects). 11 configurations are tested (RECT, L, U, podium, 1 floor, all sides): nothing stands above the roof of the lower part, the ID mask has no wrong polygon, the UVs stay in the tile.

**Русский**

* **Недостроенная часть** (`Unfinished Part`, `Side`, `Width`, `Missing Floors`; по умолчанию выкл.): одна сторона здания ниже, как будто остальное уже выросло, а эта часть ещё не построена. `Side` это +X / -X / +Y / -Y, `Width` сколько рядов модулей с этой стороны ниже, `Missing Floors` сколько этажей им не хватает. Работает для любой формы: ноги П или рукав Г могут остаться низкими, пока перемычка идёт вверх.
* В низкой части нет верхних плит, стен, лестниц, шахт, ламп, мусора и ограждений выше её собственной крыши. Колонны стоят до высоты её крыши с торчащей арматурой, стойки опалубки стоят под её собственными верхними плитами, ограждения идут по её крыше и по каждому краю ступеньки высокой части, шахты и лестницы кончаются на её крыше. Стена между низким и высоким модулем такой же высоты, как низкий.
* Хотя бы один этаж и хотя бы один ряд модулей всегда остаются полной высоты, какие бы числа ни ввели.
* Без этой опции геометрия не изменилась (побитовое сравнение, 45 из 45 объектов). Проверено 11 конфигураций (RECT, Г, П, стилобат, 1 этаж, все стороны): над крышей низкой части ничего нет, в ID-маске нет неверных полигонов, UV остаются в тайле.

## 0.21.0

**English**

* **Cut Height** (`Cut Height`, 30 m by default, 0 = off): the UVs of tall objects, first of all the columns over all floors, are cut every 30 m. A very tall island (39 m on 12 floors) used to limit the scale of the whole tile and left a free strip at the top. A building lower than 30 m (up to 9 floors of 3 m) is not cut at all, nothing changes for it (bit-for-bit comparison, 45 of 45 objects). To make the cut possible a column taller than 30 m gets an edge loop at 30 m (one polygon per side could not be cut). 12 floors: scale 0.0255 -> 0.0286 (+12%).

**Русский**

* **Высота разреза** (`Cut Height`, по умолчанию 30 м, 0 = выкл.): UV высоких объектов, прежде всего колонн на все этажи, режутся через каждые 30 м. Очень высокий островок (39 м на 12 этажах) раньше ограничивал масштаб всего тайла и оставлял свободную полосу сверху. Здание ниже 30 м (до 9 этажей по 3 м) не режется совсем, для него ничего не меняется (побитовое сравнение, 45 из 45 объектов). Чтобы разрез был возможен, колонна выше 30 м получает пояс рёбер на 30 м (одну грань на сторону резать нельзя). 12 этажей: масштаб 0.0255 -> 0.0286 (+12%).

## 0.20.1

**English**

* The default `UV Margin` is 0.005 (was 0.01): islands sit closer, the scale grows (9 x 5 x 6 building: 0.0301 -> 0.0333 tile per metre, +11%). On a tall building the scale is capped by the tallest island (a column over all floors, 39 m on 12 floors), so a smaller gap gives only +4% there.

**Русский**

* `UV Margin` по умолчанию 0.005 (было 0.01): островки лежат ближе, масштаб растёт (здание 9 x 5 x 6: 0.0301 -> 0.0333 тайла на метр, +11%). У высокого здания масштаб ограничен самым высоким островком (колонна на все этажи, 39 м на 12 этажах), поэтому там меньший зазор даёт только +4%.

## 0.20.0

**English**

* **Much better use of the UV tile (inside one material).** The islands of all groups are packed together into one free layout (a skyline packer: the tallest first, every next one into the lowest free spot), with no band per group. The scale on a 9 x 5 x 6 building is 0.0231 tile per metre against 0.0136 with bands per group (+70%); on a 12 x 6 x 12 building 0.0172 against 0.0094.
* **Floors and ceilings are separate groups.** The slabs are one object, but the group is picked per face: top = `Floors` (orange in the ID mask, material `CB_Floors`, see the table in the README), underside = `Ceilings` (violet), edge = `Concrete`. Floor and ceiling get their own texture and their own AO. `CB_Floors` carries three materials, picked per face. The exporter keeps working with one material and restores the per-face indices.
* **Split Slabs** (`Split Slabs`, `Cut Size`, on by default, 3 modules = 9 x 9 m): the UVs of the slabs are cut into pieces, identical pieces stack on each other. With the cut the scale grows to 0.0298 (61 px per metre in a 2048 texture, 28 before).
* **The ID mask is painted by the place of every stack**, not by full-width bands, so the mask follows the free layout.
* Fixed: a slab edge face could share a UV edge with a top face by chance and get the floor colour; such islands are now split by group. A test checks the mask colour under the centre of every polygon (24,000 polygons, no mismatch) in five configurations.
* The geometry did not change (45 of 45 objects are identical in a bit-for-bit comparison).

**Русский**

* **Намного лучше использование UV-тайла (в рамках одного материала).** Островки всех групп упаковываются вместе в одну свободную раскладку (упаковка по силуэту: самые высокие первыми, каждый следующий в самое низкое свободное место), без полосы на группу. Масштаб на здании 9 x 5 x 6 равен 0.0231 тайла на метр против 0.0136 с полосами на группу (+70%); на здании 12 x 6 x 12 0.0172 против 0.0094.
* **Полы и потолки это отдельные группы.** Плиты это один объект, но группа выбирается по грани: верх = `Floors` (оранжевый в ID-маске, материал `CB_Floors`, см. таблицу в README), низ = `Ceilings` (фиолетовый), торец = `Concrete`. У пола и потолка своя текстура и свой AO. У `CB_Floors` три материала, выбираемые по грани. Экспорт по-прежнему работает с одним материалом и возвращает индексы граней.
* **Резка плит** (`Split Slabs`, `Cut Size`, по умолчанию вкл., 3 модуля = 9 x 9 м): UV плит режутся на куски, одинаковые куски ложатся друг на друга. С резкой масштаб растёт до 0.0298 (61 пиксель на метр в текстуре 2048, было 28).
* **ID-маска красится по месту каждой стопки**, а не полосами на всю ширину, поэтому маска следует свободной раскладке.
* Исправлено: торец плиты мог случайно совпасть по UV-ребру с верхом и получить цвет пола; такие островки теперь делятся по группам. Тест проверяет цвет маски под центром каждого полигона (24 000 полигонов, без расхождений) в пяти конфигурациях.
* Геометрия не изменилась (45 из 45 объектов совпали при побитовом сравнении).

## 0.19.0

**English**

* **Russian interface**: switch Blender to Russian (Preferences → Interface → Language) and the panel, the tooltips, the button labels and the report messages are in Russian (128 strings, all covered by a test). With any other language the English text stays as it is. The translation is keyed by the property identifier (`translations.py`).
* **README, comments and everything else in two languages**: `README.md` (English) and `README.ru.md` (Russian), this changelog, every docstring and every code comment now have English and Russian text. Checked that the code itself did not change (identical syntax tree).
* The panel texts of `Floors` and `Seed` were out of date (the ground slab exists now; lamps and holes use the seed): corrected.
* The distribution zip was checked by installing it into a clean Blender profile (`extension install-file`) and running Rebuild from the installed copy.

**Русский**

* **Русский интерфейс**: переключите Blender на русский (Preferences → Interface → Language), и панель, подсказки, надписи кнопок и сообщения отчёта будут на русском (128 строк, все покрыты тестом). С другим языком остаётся английский текст. Перевод привязан к идентификатору свойства (`translations.py`).
* **README, комментарии и всё остальное на двух языках**: `README.md` (английский) и `README.ru.md` (русский), эта история изменений, каждый docstring и каждый комментарий в коде теперь на английском и на русском. Проверено, что сам код не изменился (одинаковое синтаксическое дерево).
* Исправлены устаревшие тексты панели у `Floors` и `Seed` (плита на земле теперь есть; лампы и отверстия используют зерно).
* Дистрибутив zip проверен установкой в чистый профиль Blender (`extension install-file`) и запуском Rebuild из установленной копии.

## 0.18.0

**English**

* **Lamps** (`CB_Lamps`): long thin boxes under the slabs, along the perimeter, parallel to the outer edge. Parameters `Lamps`, `Floors`, `Factor`, `Length`. A group of their own, magenta in the ID mask, material `CB_Lamps`.
* **Slab holes** (`Slab Holes`): random square holes for pipes, more frequent near the edge. Debris, formwork and lamps avoid the holes.
* **Podium** (`Podium`, `Podium Height`): the first storey several times taller, with the shaft and the stairs, without partitions. Walls, debris and railings from floor 2. Without a podium the geometry did not change (bit-for-bit comparison on 5 configurations).
* **Edge Bias**: random details (lamps, holes, debris) gather near the edge of the building, fewer in the centre.
* **One material on export** (`One Material`, on by default): in the FBX every object has the material `CB_Building` with the ID mask; the coloured group materials come back in Blender after the export.
* Internal: storey heights are computed in one place (`slab_top`).

**Русский**

* **Лампы** (`CB_Lamps`): длинные тонкие боксы под плитами, по периметру, параллельно наружному краю. Параметры `Lamps`, `Floors`, `Factor`, `Length`. Своя группа, пурпурный цвет в ID-маске, материал `CB_Lamps`.
* **Отверстия в плитах** (`Slab Holes`): случайные квадратные отверстия для труб, чаще у края. Мусор, опалубка и лампы обходят отверстия.
* **Стилобат** (`Podium`, `Podium Height`): первый этаж в несколько раз выше, с шахтой и лестницей, без перегородок. Стены, мусор и ограждения со 2-го этажа. Без стилобата геометрия не изменилась (побитовое сравнение на 5 конфигурациях).
* **Edge Bias**: случайные детали (лампы, отверстия, мусор) собираются у края здания, в центре их меньше.
* **Один материал при экспорте** (`One Material`, по умолчанию вкл.): в FBX у всех объектов материал `CB_Building` с ID-маской, цветные материалы групп возвращаются в Blender после экспорта.
* Внутреннее: высоты этажей считаются в одном месте (`slab_top`).

## 0.17.0

**English**

* **Shaft corner columns** (`Corner Columns`): `Trimmed` by default (they end at the roof floor, without rebar), `Removed` or `Full`. Before, the columns ended up inside the walls of the top block with the rebar sticking out of the wall. The rebar is now computed per column, so changing the mode does not change the other columns.
* The **timber formwork beams** are a separate object `CB_FormworkBeams` and a fifth group, Beams (cyan in the ID mask, material `CB_Beams`, a UV band of their own).
* UI: paired fields on one row, for example Cut (Width/Depth), Modules (X/Y), Door (Width/Height), Boards (Min/Max).

**Русский**

* **Угловые колонны шахты** (`Corner Columns`): `Trimmed` по умолчанию (кончаются на полу крыши, без арматуры), `Removed` или `Full`. Раньше колонны оказывались внутри стен верхнего блока, а арматура торчала из стены. Арматура теперь считается отдельно на каждую колонну, поэтому смена режима не меняет остальные.
* **Деревянные балки опалубки** вынесены в отдельный объект `CB_FormworkBeams` и пятую группу Beams (голубой цвет в ID-маске, материал `CB_Beams`, своя полоса UV).
* UI: парные поля в одну строку, например Cut (Width/Depth), Modules (X/Y), Door (Width/Height), Boards (Min/Max).

## 0.16.0

**English**

* **Single Mesh**: a checkbox that merges the whole building into one mesh `CB_Building` with one material (the ID mask as base colour) and one UV. Handy for Substance Painter.
* Ground slab: the thickness is back. The top and the edge faces along the contour stay, there is no bottom face (it is in the ground).
* The ID mask is 2048 by default.
* On L and U shapes the stair picks the nearest free module that has a neighbour above or below, so that it arrives on a slab.

**Русский**

* **Single Mesh**: галка, которая склеивает всё здание в один меш `CB_Building` с одним материалом (ID-маска как базовый цвет) и одной UV. Удобно для Substance Painter.
* Плита на земле: вернули толщину. Верх и боковые грани по контуру остаются, нижней грани нет (она в земле).
* ID-маска по умолчанию 2048.
* Лестница на формах Г и П выбирает ближайший свободный модуль, у которого есть сосед сверху или снизу, чтобы выходить на плиту.

## 0.15.0

**English**

* **UV by groups**: concrete, debris, formwork and railings each get their own band of the tile (`Group by Material`). One scale for all groups.
* **ID mask**: the image `CB_ID` with one colour per group (red, green, blue, yellow), saved as `<name>_ID.png` next to the FBX. Every object gets a flat material in the colour of its group (`CB_Concrete`, `CB_Debris`, `CB_Formwork`, `CB_Railings`). Parameters `ID Mask`, `Mask Size`.
* **Our own UV packing** instead of the Pack Islands operator, which did nothing in some sessions (the layout stayed unpacked). Islands are not rotated, one uniform scale, the result is always inside 0-1.
* **Stacks of similar islands** like To Stack in TechArt Tools: islands of a similar size (`Similarity`, 2%) lie on top of each other, centred, floor on floor, door on door. Parameters `Overlap Similar`, `Similarity`.
* Fixed: the gap between islands shrinks by itself when there are very many islands, otherwise the scale collapsed.

**Русский**

* **UV по группам**: бетон, мусор, опалубка и ограждения получают каждый свою полосу тайла (параметр `Group by Material`). Масштаб один на все группы.
* **ID-маска**: картинка `CB_ID` с цветом на каждую группу (красный, зелёный, синий, жёлтый), сохраняется как `<имя>_ID.png` рядом с FBX. На каждый объект ставится плоский материал цвета его группы (`CB_Concrete`, `CB_Debris`, `CB_Formwork`, `CB_Railings`). Параметры `ID Mask`, `Mask Size`.
* **Своя упаковка UV** вместо оператора Pack Islands, который в некоторых сессиях ничего не делал (раскладка оставалась неупакованной). Островки без поворота, один равномерный масштаб, результат всегда в 0–1.
* **Стопки похожих островков** как To Stack в TechArt Tools: похожие по размеру (`Similarity`, 2%) лежат друг на друге по центру, пол на пол, дверь на дверь. Параметры `Overlap Similar`, `Similarity`.
* Исправлено: зазор между островками сам уменьшается, если островков очень много, иначе масштаб схлопывался.

## 0.14.1

**English**

* UV: our own packing instead of Pack Islands (see above).

**Русский**

* UV: собственная упаковка вместо Pack Islands (см. выше).

## 0.14.0

**English**

* **Railings differ**: every span gets 1 to 3 horizontal boards and 1 to 3 vertical posts; every board has a random height, gaps and a tilt from -5° to +5°. Parameters `Boards`, `Posts`, `Tilt`.
* **Formwork beams stick out past the edge**: at the outer edge of the building every beam has its own random overhang past the slab (`Overhang`, up to 0.4 m by default). At shaft and stair openings the beams stop at the edge.
* Fixed: the tilted bars (prop legs, railing boards) did not share their vertices; now a bar has 8 vertices shared by all its faces.

**Русский**

* **Ограждения разные**: в каждом пролёте от 1 до 3 горизонтальных досок и от 1 до 3 вертикальных стоек, у каждой доски случайные высота, промежутки и наклон от −5° до +5°. Параметры `Boards`, `Posts`, `Tilt`.
* **Балки опалубки торчат за край**: на наружном краю здания у каждой балки свой случайный выступ за плиту (`Overhang`, по умолчанию до 0.4 м). В проёмах шахты и лестницы балки обрываются на кромке.
* Исправлено: у наклонных брусков (раскосы стоек, доски ограждения) вершины были не общие, теперь у бруска 8 вершин на все грани.

## 0.13.0

**English**

* Formwork props after a photo: a two-section prop (a thicker lower tube, a collar, a thinner upper one), a **tripod** of three legs (parameter `Tripods`), two layers of timber beams crossing under the slab.
* Fixed: the normals of the legs point outwards.

**Русский**

* Стойки опалубки по фото: двухсекционная стойка (нижняя труба потолще, муфта, верхняя тоньше), **тренога** из трёх раскосов (параметр `Tripods`), два слоя деревянных балок крест-накрест под плитой.
* Исправлено: у раскосов нормали смотрят наружу.

## 0.12.0

**English**

* **Formwork props** (`CB_Formwork`): under the top slabs (`Top Slabs`, 2 by default) a grid of steel props with a base and a head plate and timber beams. Parameters `Formwork Props`, `Top Slabs`, `Spacing`.
* **Railings** (`CB_Railings`): posts and three planks along the outer edge of the slabs and the edges of the stair holes; the side where the stair arrives stays open. Parameters `Railings`, `Floors`, `Height`.
* Ground slab: only the top face at Z = 0 is built (everything below is in the ground), the columns start at Z = 0.
* Fixed: a box left loose vertices in the mesh when some of its faces were not built.

**Русский**

* **Стойки опалубки** (`CB_Formwork`): под верхними плитами (`Top Slabs`, по умолчанию 2) сетка стальных стоек с опорной и верхней плитой и деревянными балками. Параметры `Formwork Props`, `Top Slabs`, `Spacing`.
* **Ограждения** (`CB_Railings`): столбики и три доски по наружному краю плит и по краям лестничных проёмов, сторона выхода лестницы остаётся открытой. Параметры `Railings`, `Floors`, `Height`.
* Плита на земле: строится только верхняя грань на Z = 0 (всё ниже в земле), колонны начинаются на Z = 0.
* Исправлено: бокс оставлял в меше висящие вершины, если часть его граней не строилась.

## 0.11.0

**English**

* **Ground slab** (`Ground Slab`, on by default): a slab at the zero level, top at Z = 0, so that the building stands on the ground. It is solid, there is no hole under a shaft or stair. The columns start inside the slab (the lowest point is minus the slab thickness). The heights of walls, stairs and debris do not change.

**Русский**

* **Плита на земле** (`Ground Slab`, по умолчанию вкл.): плита на нулевом уровне, верх на Z = 0, чтобы здание стояло на земле. Она сплошная, под шахтой и лестницей дыры нет. Колонны начинаются внутри плиты (нижняя точка -толщина плиты). Высоты стен, лестниц и мусора не меняются.

## 0.10.0

**English**

* Stairs: a new main style, **Concrete Flight**, a solid concrete flight (steps on an inclined slab, the underside of the landing and of the flight in one plane) after a reference. The previous style is available as **Blocks**. Parameter `Style`.
* Steps are twice as small: about 0.19 m (8 per flight instead of 4 blocks of 0.375 m) in both styles.
* A stair takes its module from edge to edge, the landing rests against the corner columns (before there was a 0.3 m gap between them).
* The flight has no hidden end faces and no underground part of the first riser.

**Русский**

* Лестницы: новый основной стиль **Concrete Flight**, цельный бетонный марш (ступени на наклонной плите, низ площадки и марша в одной плоскости) по референсу. Прежний стиль доступен как **Blocks**. Параметр `Style`.
* Ступени вдвое мельче: около 0.19 м (8 на марш вместо 4 блоков по 0.375 м) в обоих стилях.
* Лестница занимает модуль от кромки до кромки, площадка упирается в угловые колонны (раньше между ними была щель 0.3 м).
* У марша нет скрытых торцевых граней и подземной части первой подступенки.

## 0.9.0

**English**

* Step 4: the **building shapes** L (L-shape) and U (U-shape), parameters `Shape`, `Cut Width`, `Cut Depth`. The cut limits itself. Shafts and stairs move to the nearest module if the building has none at the wanted place.
* **Fire stairs**: a hole in every slab, the stair is built up to the floor `Built Up To Floor`, above it only the hole remains. Two flights of big blocks and a half landing on every floor. `Position`: in the centre, at the edge or at both ends. A new object `CB_Stairs`, the shared UV map and the FBX.

**Русский**

* Шаг 4: **формы здания** Г (L-shape) и П (U-shape), параметры `Shape`, `Cut Width`, `Cut Depth`. Вырез ограничивается сам. Шахты и лестницы сдвигаются на ближайший модуль, если в нужном месте здания нет.
* **Пожарные лестницы**: дыра в каждой плите, лестница построена до этажа `Built Up To Floor`, выше остаётся только дыра. Два марша из крупных блоков и половинная площадка на каждый этаж. Положение `Position`: по центру, с края или на обоих торцах. Новый объект `CB_Stairs`, общая UV-карта и FBX.

## 0.8.0

**English**

* Shafts end in a **top block with a door**: above the roof the shaft rises by `Top Block` (3 m by default, `Shaft Top Extension` = 1 m before) and the block has a door like the other floors. A block lower than 1.5 m stays solid. The parameter was renamed `Top Block`; the old value in saved scenes does not change.

**Русский**

* Шахты кончаются **верхним блоком с дверью**: над крышей шахта поднимается на высоту `Top Block` (по умолчанию 3 м, раньше `Shaft Top Extension` = 1 м) и в блоке есть дверь, как на остальных этажах. Блок ниже 1.5 м остаётся глухим. Параметр переименован в `Top Block`, старое значение сохранённых сцен не меняется.

## 0.7.0

**English**

* **Debris**: construction debris, boxes without a bottom face on the floors. Parameters: `Floors` (numbered like walls, 1 = ground, the last = roof), `Factor` (share of modules with a box), height (0.5-2 m), length (1-2 m) and width ranges. A new object `CB_Debris`, the shared UV map and the FBX.

**Русский**

* **Debris**: строительный мусор, боксы без нижней грани на полах. Параметры: `Floors` (этажи, нумерация как у стен, 1 = земля, последний = крыша), `Factor` (доля модулей с боксом), диапазоны высоты (0.5–2 м), длины (1–2 м) и ширины. Новый объект `CB_Debris`, общая UV-карта и FBX.

## 0.6.0

**English**

* Walls: the parameter `Wall Chance` (share of the inner edges with a wall, 1 by default). The layout is the same on every floor.
* The randomness of walls and doors is tied to the element and `Seed`: changing the floors with walls, `Clear Walls` or `Wall Chance` does not reshuffle the rest. Because of this, with the same `Seed` the doors are not where they were in 0.5.0.

**Русский**

* Стены: параметр `Wall Chance` (доля внутренних рёбер со стеной, по умолчанию 1). Раскладка одинакова на всех этажах.
* Случайность стен и дверей привязана к элементу и `Seed`: смена этажей со стенами, `Clear Walls` или `Wall Chance` остальное не перемешивает. Из-за этого при том же `Seed` двери стоят не там, где в 0.5.0.

## 0.5.0

**English**

* Shafts: **a door on every floor** (side `Door Side`), the opening goes right through, the topology is like the walls'. The shaft sides are split by the levels of the floors and the slabs.
* Shafts: a count (`Count`) and a gap between them (`Padding`, 3, 9, 18 m) instead of a list of modules. The list stays as the optional field `Custom Modules`. With the default settings the shaft stands where it did (module 2,2 at 4×3).
* No interior walls within `Clear Walls` modules around the shafts (1 by default), so the shaft is visible.

**Русский**

* Шахты: **дверь на каждом этаже** (сторона `Door Side`), проём сквозной, топология как у стен. Стороны шахты разбиты по уровням этажей и перекрытий.
* Шахты: число (`Count`) и отступ между ними (`Padding`, 3, 9, 18 м) вместо списка модулей. Список остался как необязательное поле `Custom Modules`. С настройками по умолчанию шахта стоит на прежнем месте (модуль 2,2 при 4×3).
* Внутренние стены не строятся в радиусе `Clear Walls` модулей вокруг шахт (по умолчанию 1), чтобы шахту было видно.

## 0.4.0

**English**

* Step 3: **elevator shafts**. A hollow tube around a module (parameters `Shaft Modules`, `Shaft Wall`, `Shaft Top Extension`), the object `CB_Shafts`. A hole in the slabs under the shaft, no interior walls on the shaft edges. The shared UV map and the FBX.
* Door topology: three quads per side with borders from the top corners of the wall to the top corners of the opening, no extra vertices on the top edge.

**Русский**

* Шаг 3: **лифтовые шахты**. Полая труба вокруг модуля (параметры `Shaft Modules`, `Shaft Wall`, `Shaft Top Extension`), объект `CB_Shafts`. В плитах под шахтой дыра, внутренние стены на рёбрах шахты не строятся. Общая UV-карта и FBX.
* Топология двери: три четырёхугольника на сторону с границами от верхних углов стены к верхним углам проёма, на верхнем ребре нет лишних вершин.

## 0.3.0

**English**

* Step 2: **walls**. Interior only (on the inner grid edges), on the chosen floors (`Wall Floors`). Two kinds: solid and with a door opening, picked at random by `Seed` and `Door Chance`. A new object `CB_Walls`, the shared UV map and the FBX.
* The height of every rebar rod is random: `Rebar Height` ± `Height Random` (0.1 m by default).
* The columns lost their bottom face (the foot goes into the ground).

**Русский**

* Шаг 2: **стены**. Только внутренние (по внутренним рёбрам сетки), на выбранных этажах (`Wall Floors`). Два вида: глухая и с дверным проёмом, выбор случайный по `Seed` и `Door Chance`. Новый объект `CB_Walls`, общая UV-карта и FBX.
* Высота каждого прута арматуры случайная: `Rebar Height` ± `Height Random` (по умолчанию 0.1 м).
* У колонн убрана нижняя грань (низ уходит в землю).

## 0.2.0

**English**

* Columns of different heights above the top slab: parameters `Height Variation` and `Seed`.
* Rebar: 9 rods (a 3×3 grid, simple boxes without a bottom face) on top of every column, one smoothing group. Parameters `Rebar`, `Rebar Height`, `Rebar Size`.

**Русский**

* Колонны над верхней плитой разной высоты: параметры `Height Variation` и `Seed`.
* Арматура: 9 прутьев (сетка 3×3, простые боксы без нижней грани) на верхушке каждой колонны, одна группа сглаживания. Параметры `Rebar`, `Rebar Height`, `Rebar Size`.

## 0.1.3

**English**

* UV: slabs and columns are packed **together into one 0-1 tile**. Before, every object took the whole tile and they overlapped.
* Our own box projection in world metres (1 m = 1 UV unit): slabs and columns have the same texel density. The built-in Cube Projection in multi-object mode gave the slabs a scale about 8 times smaller.
* After packing the UVs are forced into 0-1 with a uniform scale, whatever the Pack Islands operator returned (in the UI the islands ended up outside the tile).

**Русский**

* UV: плиты и колонны упаковываются **вместе, в один тайл 0–1**. Раньше каждый объект занимал весь тайл, и они накладывались.
* Своя Box Projection в метрах мира (1 м = 1 UV-единица): у плит и колонн одинаковая плотность текселей. Штатная Cube Projection в мульти-объектном режиме давала у плит масштаб примерно в 8 раз мельче.
* После упаковки UV принудительно вписываются в 0–1 равномерным масштабом, независимо от результата оператора Pack Islands (в интерфейсе островки оказывались за пределами тайла).

## 0.1.1

**English**

* Fixed a panel error: `use_property_decorator` was replaced by `use_property_decorate`, the panel did not open.
* The extension version is shown in the panel.

**Русский**

* Исправлена ошибка панели: `use_property_decorator` заменён на `use_property_decorate`, панель не открывалась.
* Версия расширения показывается в панели.

## 0.1.0

**English**

* Step 1: the frame of a rectangular building. Slabs (3×3 m modules stitched into one mesh) and columns at the grid nodes.
* Box projection and UV packing into one tile on every object.
* The buttons Rebuild, Export FBX, Open Folder.

**Русский**

* Шаг 1: каркас прямоугольного здания. Плиты (модули 3×3 м, сшиты в один меш) и колонны в узлах сетки.
* Box Projection и упаковка UV в один тайл на каждом объекте.
* Кнопки Rebuild, Export FBX, Open Folder.
