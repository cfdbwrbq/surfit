Форматы файлов
==============

Собственный формат — это файл данных surfit. ``file_save`` и ``file_load``
пишут и читают всю задачу — данные, правила и результат; ``surf_save`` и
``surf_load`` сохраняют одну поверхность, а у каждого типа данных есть свои
``<type>_save`` и ``<type>_load``. Всё остальное даёт плагин ``surfit_io``,
который Tcl-фронтенд загружает отдельно, а пакет Python включает в себя.

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

Имена команд различаются приставкой по типу данных: ``pnts_``, ``curv_``,
``cntr_`` и ``area_``. Набор форматов у типов не одинаков:

* **собственный surfit** — у всех четырёх: ``<type>_load`` и ``<type>_save``.
* **текст с колонками** — у всех четырёх: ``<type>_read`` и ``<type>_write``.
* **Surfer BLN** — у кривых, изолиний и площадей: ``curv_*_bln``,
  ``cntr_*_bln``, ``area_*_bln``. У точек нет ни чтения, ни записи BLN.
* **ESRI shapefile** — у всех четырёх: ``<type>_load_shp`` и
  ``<type>_save_shp``.

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

Цифровые модели рельефа
-----------------------

DEM приходят из библиотеки ``globe``, которую Tcl-фронтенд загружает отдельно,
а пакет Python включает. Это геопривязанные растры, а не поверхности:
загрузчик сохраняет начало и шаг тайла.

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - Формат
     - Загрузка
     - Сохранение
   * - собственный surfit
     - ``dem_load``
     - ``dem_save``
   * - сетка Surfer
     - ``dem_load_grd``
     - ``dem_save_grd``
   * - DTM
     - ``dem_load_dtm``
     - ``dem_save_dtm`` (не реализовано)
   * - тайл SRTM HGT
     - ``dem_load_hgt``
     - --
   * - сжатый тайл SRTM HGT
     - ``dem_load_hgt_zip``
     - --
   * - GTOPO30 / GLOBE
     - ``dem_load_globe``
     - --
   * - три колонки xyz
     - --
     - ``dem_save_xyz``

Две оговорки относятся к самим форматам. ``dem_load_hgt_zip`` требует сборки с
заголовками zlib; без них он сообщает «zlib not detected» и ничего не
возвращает. ``dem_save_dtm`` объявлен в заголовках, но реализация пишет
«Not implemented!» и возвращает false, поэтому тайл DTM можно прочитать, но не
записать.

Загрузчики DEM принимают шаблон файла и находят тайл по имени; для тайла HGT
имя несёт ещё и координаты. Подробности — в :doc:`python`.

Маски
-----

``mask_save`` пишет маску в собственный файл; ``mask_save_grd`` и
``mask_save_xyz`` — сетку Surfer или xyz из трёх колонок. ``mask_load`` читает
маску обратно из файла данных surfit.

Чтение каталога
---------------

Большинство загрузчиков — и плагин форматов, и загрузчики DEM — принимают в
имени файла шаблон оболочки вместо одного пути и возвращают по флагу на каждый
найденный файл:

.. code-block:: python

   flags = surfit.area_read("zones/*.c*")
   assert all(flags)

Имена в этом случае выводятся из имён файлов, поскольку явное имя не задано.

Готовые примеры
---------------

Шесть круговых рейсов из ``examples/python/`` показывают плагин со стороны
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

cntr_shp.py
~~~~~~~~~~~

Пять изолиний читаются, три с именами ``cntr_*`` пишутся в один шейпфайл и
возвращаются из него со своими Z. Набор смешивает плоские изолинии с одной
переменной по Z — именно на таком наборе сейвер и падал:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/cntr_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/cntr_shp.tcl
         :language: tcl-src

Один исходный скрипт не перенесён: ``const_cntr.tcl`` читает шейпфайл, которого
нет в репозитории. Два примера с шейпфайлами выше тоже пришлось починить:
``area_shp`` и ``curv_shp`` называли вывод ``.bln``, а читатель принимает имя
как шаблон файла и поэтому молча ничего не загружал. Теперь оба называют файл
``.shp``, а сгенерированный ``curvs.bln``, который нёс дистрибутив, удалён,
чтобы BLN-пример начинался с чистого листа.

``cntr_shp.py`` заодно проверяет исправление в сейвере. Раньше он выбирал тип
шейпа по первой изолинии, поэтому набор из плоских и переменной по Z изолиний
падал на середине и оставлял частичный файл. Теперь ``cntr_save_shp`` сначала
решает тип по всем найденным изолиниям (ARCZ, если хоть одна меняет Z), а затем
пишет их все этим типом; плоская изолиния пишется как ARCZ со своим постоянным
Z. При загрузке такого файла ``zfield`` не нужен; аргумент остаётся для
2D-файлов, записанных старыми версиями.
