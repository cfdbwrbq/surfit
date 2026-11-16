Переход с Tcl
=============

Статус
------

Tcl-фронтенд **заморожен**. Линия 3.7.x — последняя с Tcl; surfit 3.8 удаляет
Tcl-модуль, SWIG-биндинги, Tcl-примеры и опцию ``SURFIT_BUILD_TCL``.
Python-пакет и колёса это не затрагивает.

Что меняется
------------

- Сборка из исходников больше не принимает ``-DSURFIT_BUILD_TCL=ON``.
- Исчезают ``libtclsurfit``, Tcl-плагины и интерпретатор ``surfit``.
- Исчезают ``.tcl``-примеры и Tcl-часть parity-тестов.
- Python-команды, форматы и численное поведение остаются прежними.

Перенос скрипта
---------------

В Tcl и Python одинаковые имена команд. Tcl-задача становится
``surfit.Session``; аргументы команд не меняются.

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Tcl
     - Python
   * - ``grid_get -12 12 0.2 -12 12 0.2``
     - ``task.grid(-12, 12, 0.2, -12, 12, 0.2)``
   * - ``area_read "data/area1.txt" "area1"``
     - ``task.read_areas("data/area1.txt", "area1")``
   * - ``area 10 "area1"``
     - ``task.area(10, "area1")``
   * - ``completer 1 1.6``
     - ``task.completer(1, 1.6)``
   * - ``surfit``
     - ``task.solve()``
   * - ``surf_save "area.dat" "map_area"``
     - ``task.save("area.dat")``

Полный API — в Python guide; общие имена команд — в command reference.

Что остаётся
------------

- Все форматы данных и численные правила.
- Python-имена, унаследованные от Tcl (``pnts_*``, ``area_*``, ``curv_*``).
- Тег 3.7.2 как последний релиз с Tcl.
