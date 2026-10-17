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

Готовые примеры
---------------

Пять круговых рейсов из ``examples/python/`` показывают плагин со стороны
Python. Каждый читает текстовые данные, пишет файл, сбрасывает данные и читает
файл обратно, поэтому вторая запись и есть доказательство, что читатель и
писатель согласованы. ``test_examples.py`` запускает каждый из них вместе с
Tcl-оригиналом и сравнивает все записанные файлы побайтово.

Писатель BLN дописывает в файл, а не перезаписывает его, поэтому пример
рассчитан на каталог, где его вывода ещё нет; тест даёт обеим сторонам чистый
каталог.

area_bln.py
~~~~~~~~~~~

Пять полигонов читаются, ``area1`` пишется в ``areas.bln``, данные
сбрасываются, файл читается обратно и снова пишется как ``areas2.bln``:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/area_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/area_bln.tcl
         :language: tcl-src

cntr_bln.py
~~~~~~~~~~~

Пять изолиний вместе со своими значениями Z уходят в один BLN-файл и
возвращаются из него:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/cntr_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/cntr_bln.tcl
         :language: tcl-src

curv_bln.py
~~~~~~~~~~~

Четыре кривые записываются, а три загружаются обратно по шаблону имени —
шаблон файла и шаблон имени независимы:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/curv_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/curv_bln.tcl
         :language: tcl-src

area_shp.py
~~~~~~~~~~~

Шейпфайл — это три файла. Писатель берёт базовое имя и создаёт ``.shp``,
``.shx`` и ``.dbf``; читатель принимает шаблон файла, поэтому оба вызова
называют файл ``.shp``:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/area_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/area_shp.tcl
         :language: tcl-src

curv_shp.py
~~~~~~~~~~~

То же для четырёх кривых, три загружаются обратно:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/curv_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/curv_shp.tcl
         :language: tcl-src

Два исходных скрипта не перенесены. ``cntr_shp.tcl`` смешивает плоскую
2D-изолинию с 3D, а ``cntr_save_shp`` фиксирует тип шейпа по первой изолинии,
поэтому набор не пишется в один файл — это открытый дефект. ``const_cntr.tcl``
читает шейпфайл, которого нет в репозитории. Два примера с шейпфайлами выше
тоже пришлось починить: исходные скрипты называли вывод ``.bln``, а читатель
принимает имя как шаблон файла и поэтому молча ничего не загружал. Теперь оба
называют файл ``.shp``, а сгенерированный ``curvs.bln``, который нёс дистрибутив,
удалён, чтобы BLN-пример начинался с чистого листа.
