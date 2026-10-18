"""Read points from PostgreSQL/PostGIS through the psql client.

The helper deliberately has no Python dependency: it runs ``psql`` (which
already knows how to read ``.pgpass`` and service files), asks for the result as
CSV, and feeds the rows through the same loader as ``pnts_read``.
"""
import contextlib
import csv
import io
import os
import shutil
import subprocess
import tempfile

from surfit import pnts_read


def _find_psql(psql):
    executable = shutil.which(psql)
    if executable is None:
        raise RuntimeError(
            "read_postgis needs the psql client; %r is not on PATH" % (psql,))
    return executable


def _query_statement(query):
    statement = query.strip().rstrip(";")
    if not statement:
        raise ValueError("read_postgis: the query is empty")
    return statement


def _copy_command(statement, timeout):
    timeout_ms = max(1, int(timeout)) * 1000
    return (
        "SET default_transaction_read_only = on; "
        "SET statement_timeout = %d; "
        "COPY (%s) TO STDOUT WITH (FORMAT csv);"
        % (timeout_ms, statement)
    )


def _run_psql(executable, conninfo, command, timeout):
    run_result = subprocess.run(
        [
            executable,
            "--no-psqlrc",
            "--no-password",
            "--quiet",
            "--tuples-only",
            "--no-align",
            "--dbname", conninfo,
            "--command", command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if run_result.returncode != 0:
        detail = run_result.stderr.strip() or run_result.stdout.strip()
        raise RuntimeError(
            "read_postgis: psql failed with exit %d: %s"
            % (run_result.returncode, detail))
    return run_result.stdout


def _remove(path):
    with contextlib.suppress(OSError):
        os.unlink(path)


def _write_points(rows):
    file_handle, path = tempfile.mkstemp(prefix="surfit-postgis-", suffix=".txt")
    try:
        with os.fdopen(file_handle, "w", encoding="utf-8") as stream:
            for point in rows:
                stream.write("%.17g\t%.17g\t%.17g\n" % point)
    except Exception:
        _remove(path)
        raise
    return path


def _load_points(path, name):
    try:
        points = pnts_read(path, name)
    except Exception:
        _remove(path)
        raise
    _remove(path)
    return points


def read_postgis(conninfo, query, name="points", psql="psql", timeout=300):
    """Reads points from a PostgreSQL/PostGIS query into the task.

    ``query`` must return exactly three columns, x, y and z, in that order.  It
    may read PostGIS geometry::

        SELECT ST_X(geom), ST_Y(geom), COALESCE(ST_Z(geom), 0)
        FROM wells WHERE geom IS NOT NULL

    or plain numeric columns.  ``conninfo`` is a libpq connection string (for
    example ``"service=surfit dbname=gis"``); the password comes from
    ``.pgpass`` or the service file, never from this call.

    The query runs with ``--no-password`` in a read-only transaction, and the
    whole result is fetched before the engine is called.  For a very large table
    read it in slices instead.  A missing ``psql``, a failed query, a result
    that is not three numeric columns, a NULL coordinate and an empty result all
    raise instead of silently loading nothing.
    """
    executable = _find_psql(psql)
    rows = _parse_csv(_run_psql(
        executable,
        conninfo,
        _copy_command(_query_statement(query), timeout),
        timeout,
    ))
    if not rows:
        raise ValueError("read_postgis: the query returned no points")
    return _load_points(_write_points(rows), name)


def _parse_row(number, row):
    """Converts one CSV row into a (x, y, z) float triple."""
    if len(row) != 3:
        raise ValueError(
            "read_postgis: row %d has %d columns, expected x, y, z"
            % (number, len(row)))
    try:
        point_x, point_y, point_z = (float(raw_value) for raw_value in row)
    except ValueError:
        raise ValueError(
            "read_postgis: row %d is not numeric: %r" % (number, row)) from None
    return point_x, point_y, point_z


def _parse_csv(text):
    """Turns COPY's CSV output into (x, y, z) float triples."""
    rows = []
    reader = csv.reader(io.StringIO(text))
    for number, row in enumerate(reader, 1):
        if not row:
            continue
        rows.append(_parse_row(number, row))
    return rows
