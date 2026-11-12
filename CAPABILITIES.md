# Возможности surfit

## Ядро

### Что решает

- строит регулярную 2.5D-сетку из рассеянных данных;
- значение поверхности постоянно внутри ячейки;
- интерполяция и приближение, а не только «пройти через точки»;
- один solve — одна поверхность на одной сетке;
- неопределённые ячейки хранятся как `UNDEF_VALUE`.

### Входные данные

- точки XYZ;
- 2D-кривые;
- 3D-контуры (Z — значение);
- площади-полигоны;
- поверхности и тренды;
- маски;
- гистограммы;
- DEM через модуль `globe` (опционально);
- разломы как линии, через которые поверхность может прыгать.

### Правила (gridding rules)

- точки: интерполяция, приближение с весом, верхние/нижние границы;
- кривые: значение вдоль линии, границы, разломы;
- контуры: значение вдоль 3D-линии, границы;
- площади: константа внутри/снаружи, `undef`, среднее, взвешенное среднее, следование поверхности, сглаживание только внутри площади, гистограмма, границы;
- поверхности: следование поверхности, тренд, анизотропия;
- маски: ограничение правила, вырезание отверстий, средние и границы;
- гистограммы: подгонка распределения;
- `completer`: сглаживание через D1 (наклон) и D2 (кривизна);
- условия-неравенства, средние и штрафные ограничения;
- порядок добавления правил задаёт приоритет.

### Решатель

- CMOFS: последовательная минимизация функционалов;
- многоуровневая схема: 8×8, затем удвоение до нужной сетки;
- penalty-loop для ограничений;
- пять итеративных методов: `cg`, `jcg`, `rf`, `jacobi`, `ssor`;
- настройка допуска, числа penalty-итераций и множителя;
- `tol` — допуск шага, а не гарантированная ошибка результата;
- thread-local состояние движка;
- независимые задачи могут решаться параллельно;
- OpenMP не используется: горячий matvec уже многопоточный через `sstuff`, причина и цифры — в `docs/en/development.rst`.

### Выход и форматы

- регулярная сетка в памяти;
- native surfit data file;
- Surfer GRD;
- GMT;
- Grass;
- ArcGIS;
- xyz;
- shapefile;
- BLN;
- JPEG/BMP;
- NetCDF — при наличии опциональной зависимости;
- сохранение/загрузка всей задачи, сетки, масок и гистограмм.

### Два фронтенда

- исходный Tcl-фронтенд (опциональная сборка);
- Python-пакет поверх того же C++-ядра;
- одинаковые имена команд;
- побайтовое сравнение результатов Tcl и Python в тестах.

## Python-обвязка

### Задача и сетка

- `Session` — отдельная задача со своим состоянием;
- `grid`, `grid_auto`, `grid_get`, `grid_get2`;
- `values()` возвращает numpy-массив `(count_y, count_x)`;
- `defined_mask`, `UNDEF_VALUE`;
- `add_surface` — сетка/тренд из numpy;
- `add_points`, `add_curves`, `add_areas`, `add_contours` — данные из numpy без временных файлов;
- веса точек;
- `strict=True` для ошибки на пустом совпадении правил;
- `serial=True` для одного worker’а в задаче;
- `progress()` и `viewer()`.

### Все команды Tcl

- доступны как функции модуля и методы `Session`;
- чтение/запись всех поддерживаемых форматов;
- `pnts_*`, `curv_*`, `cntr_*`, `area_*`, `surf_*`, `mask_*`, `hist_*`, `dem_*`;
- примеры Tcl переводятся в Python один-к-одному;
- runner сравнивает результаты с Tcl побайтово.

### Качество и валидация

- остатки в точках: RMSE, bias, weighted MSE, chi², dof;
- поиск выбросов;
- robust-веса и внешний IRLS;
- spatial CV: random, kfold, block, group;
- leave-one-group-out;
- подбор параметра сглаживания по CV;
- per-node support;
- declustering: nearest, mean, min, max, IDW;
- polygonal declustering (2D, SciPy опционально, есть fallback);
- typed point diagnostics;
- GeoJSON/CSV для диагностики;
- quality report с provenance и хешами входных файлов;
- per-node support и coverage.

### Неопределённость

- bootstrap-ансамбль;
- block bootstrap;
- split-conformal quantile;
- симметричный и асимметричный calibrated interval;
- empirical coverage;
- coverage по группам;
- group-conformal quantiles;
- интервалы внутри `SurfaceStack`;
- конфликты интервалов на отношениях слоёв.

### Пространственные диагностики остатков

- Moran's I для регулярной сетки;
- экспериментальная вариограмма остатков;
- расстояние до ближайшей точки данных;
- ошибка по полосам расстояния;
- bias/MAE/RMSE по группам.

### Объёмы, разрезы и интеграции

- объём между двумя поверхностями или до контакта;
- объём по маске;
- P10/P50/P90 только по когерентным реализациям;
- `volume_ensemble`, `volume_percentiles`;
- разрезы `SurfaceStack` по ломаной;
- интервалы и слои в разрезе;
- `rule_report()` — порядок правил, типы, conditions, residual и violations там, где они известны;
- `add_dip_points` / `add_gradient_points` — локальные производные;
- `gradient()` — soft-условие на dZ/dx и dZ/dy;
- `slope_max()` и `curvature_max()` — penalty-условия локальных границ (глобально или внутри area/mask);
- условия добавляются до `completer`, solver делает base solve для их построения;
- GeoPandas/Shapely адаптер (опционально);
- CRS-проверка без тихого перепроецирования;
- xarray `Dataset` и Zarr export (опционально);
- regression-тренд + residual wrapper (OLS или sklearn-модель);
- `add_regression_residuals`;
- `SurfaceEnsemble` — когерентная арифметика, проценты, объёмы, изохоры;
- `run_recipe` / `surfit run` — JSON/YAML-рецепты задач;
- `grid_mesh` / `export_gltf` / `export_obj` / `export_stl` — 3D-экспорт;
- `stack.to_pyvista()` — опциональный PyVista/VTK.

### Слоистые поверхности

- `SurfaceStack`: несколько слоёв на одной сетке;
- crossings, thickness, pinch-outs;
- DAG-отношения `above`/`below`;
- minimum thickness;
- топологическая сортировка и обнаружение циклов;
- несколько условий на слой через `SurfaceRelations`;
- параллельный solve независимых слоёв;
- pinch-out projection `merge`/`undef`;
- сохранение `.npy` + `manifest.json`;
- memory-mapped значения и chunked report;
- `validate()` с typed violations и `StackValidationError`;
- per-layer provenance;
- calibrated intervals и relation conflicts;
- benchmark direct/sequential/parallel.

### Растровый обмен

- `read_geotiff`;
- `save_geotiff`;
- `save_geotiff_stack` — по файлу на слой + manifest;
- `save_geotiff_bands` — multi-band GeoTIFF;
- COG через GDAL;
- `tifffile` fallback без GDAL для пикселей и scale/tiepoint;
- CRS без GDAL не теряется молча — будет ошибка;
- north-up/cell-centre конвенция;
- rotated/west-up GeoTIFF читается через GDAL warp;
- `target_extent` и `resample` для явной регулярной сетки;
- результат помечает `rotated`, `resampled`, `resampling`;
- запись пока north-up.

### Большие данные

- tiled solve с перекрытием;
- запись мозаики в memmap;
- memory-mapped слои stack;
- chunked report;
- параллельные независимые `Session`.

### Вспомогательное

- CRS helpers через pyproj (опционально);
- `grid collar` и проверка разрешения;
- `viewer()` — автономный HTML;
- `save_viewer`, `save_report`, `save_metadata`;
- `save_geotiff` из метаданных задачи.

## Ограничения

- только 2.5D, без 3D voxel/octree;
- нет mesh/CAD export;
- нет ML/property prediction;
- нет GUI/map composition;
- slope/curvature bounds — penalty-условия, не post-solve проекция;
- rule report показывает residual для conditional-правил и violations для известных inequality-правил; для non-penalty data-правил residual = None;
- P10/P50/P90 нельзя получить сложением per-cell интервалов;
- GeoPandas, xarray, Zarr и sklearn — опциональны;
- один solver, без kriging-ковариационной модели;
- GDAL, SciPy, pyproj, tifffile — опциональны;
- Linux x86_64 — основная платформа;
- GPL-2.

## Где смотреть дальше

- `README.md` — быстрый старт;
- `docs/en/python.rst` — полный Python-гайд;
- `docs/en/how_it_works.rst` — CMOFS, penalty-loop и solvers;
- `docs/en/commands.rst` — все команды;
- `docs/` — полная документация;
- `examples/python/` — запускаемые примеры.
