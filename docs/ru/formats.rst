Форматы файлов
==============

Собственный формат — это файл данных surfit, который пишут и читают
``surf_save`` и ``surf_load`` со товарищи; в нём хранится вся задача, а не
только сетка. Всё остальное даёт плагин ``surfit_io``, который Tcl-фронтенд
загружает отдельно, а пакет Python включает в себя.

Сетки и поверхности
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 34 36

   * - Формат
     - Загрузка
     - Сохранение
   * - собственный surfit
     - ``surf_load``
     - ``surf_save``
   * - сетки Surfer, текстовые и двоичные (v6, v7)
     - ``surf_load_grd``
     - ``surf_save_grd``
   * - GMT grd
     - ``surf_load_gmt``
     - ``surf_save_gmt``
   * - Grass ASCII
     - ``surf_load_grass``
     - ``surf_save_grass``
   * - ArcGIS ASCII grid
     - ``surf_load_arcgis``
     - ``surf_save_arcgis``
   * - три колонки xyz
     - ``surf_load_xyz``
     - ``surf_save_xyz``
   * - JPEG (пиксели становятся высотами)
     - ``surf_load_jpg``
     - ``surf_save_jpg``
   * - BMP (пиксели становятся высотами)
     - ``surf_load_bmp``
     - ``surf_save_bmp``

Точки, кривые, изолинии и площади
---------------------------------

У этих четырёх семейств один и тот же набор форматов, а имена команд
различаются приставкой по типу данных: ``pnts_``, ``curv_``, ``cntr_`` и
``area_``.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Формат
     - Загрузка
     - Сохранение
   * - собственный surfit
     - ``<type>_load``
     - ``<type>_save``
   * - текст с колонками
     - ``<type>_read``
     - ``<type>_write``
   * - Surfer BLN
     - ``<type>_load_bln``
     - ``<type>_save_bln``
   * - ESRI shapefile
     - ``<type>_load_shp``
     - ``<type>_save_shp``

``<type>_read`` и ``<type>_write`` работают с текстовыми файлами с колонками и
принимают номера колонок и разделитель; по умолчанию это первые колонки и
пробельные символы:

.. code-block:: tcl

   pnts_read "model.txt" "model" 3 4 8 2 "\t" 1

Здесь x, y и z читаются из колонок 3, 4 и 8, колонка 2 переносится следом,
разделитель — табуляция, одна строка заголовка пропускается. В Python тот же
вызов выглядит так:

.. code-block:: python

   surfit.pnts_read("model.txt", "model", col1=3, col2=4, col3=8, col4=2,
                    delimiter="\t", skip_lines=1)

Маски
-----

``mask_save_grd`` и ``mask_save_xyz`` записывают растровые маски;

``mask_load`` читает маску обратно из файла данных surfit.

Чтение каталога
---------------

Загрузчики принимают в имени файла шаблон оболочки вместо одного пути и
возвращают по флагу на каждый найденный файл:

.. code-block:: python

   flags = surfit.area_read("zones/*.c*")
   assert all(flags)

Имена в этом случае выводятся из имён файлов, поскольку явное имя не задано.
