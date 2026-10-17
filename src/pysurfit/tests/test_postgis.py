"""Tests the psql-backed point reader without a database.

A tiny fake psql on PATH prints the CSV the helper would get from COPY, so the
query wrapper, parsing, error paths and the point loader are exercised here;
the real database is only needed for the opt-in manual example.
"""
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def make_psql(directory, output):
    """A stand-in for psql: records its arguments and prints `output`."""
    path = os.path.join(directory, "psql")
    log = os.path.join(directory, "psql.log")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "with open(os.environ['FAKE_PSQL_LOG'], 'w', encoding='utf-8') as f:\n"
            "    f.write('\\n'.join(sys.argv))\n"
            "sys.stdout.write(os.environ['FAKE_PSQL_OUT'])\n"
        )
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    os.environ["FAKE_PSQL_LOG"] = log
    os.environ["FAKE_PSQL_OUT"] = output
    return path, log


def expect(exception, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except exception as error:
        return error
    raise AssertionError("expected %s" % exception.__name__)


def main():
    surfit.clear_data()
    with tempfile.TemporaryDirectory() as directory:
        psql, log = make_psql(directory, "1.5,2.5,3.5\n-4,5,6\n")
        flags = surfit.read_postgis(
            "dbname=test", "SELECT x, y, z FROM points", name="db",
            psql=psql)
        assert flags == [True], flags
        assert surfit.pnts_size() == 1
        assert surfit.pnts_minx("db") == [-4.0]
        assert surfit.pnts_maxz("db") == [6.0]

        arguments = open(log, encoding="utf-8").read()
        assert "--no-password" in arguments
        assert "default_transaction_read_only = on" in arguments
        assert "COPY (SELECT x, y, z FROM points)" in arguments
        print("PASS: points load, values arrive, the query is read-only")

        surfit.clear_data()
        with tempfile.TemporaryDirectory() as second:
            psql, _ = make_psql(second, "1,2\n")
            expect(ValueError, surfit.read_postgis,
                   "dbname=test", "SELECT 1", psql=psql)

            psql, _ = make_psql(second, "1,2,\n")
            expect(ValueError, surfit.read_postgis,
                   "dbname=test", "SELECT 1", psql=psql)

            psql, _ = make_psql(second, "")
            expect(ValueError, surfit.read_postgis,
                   "dbname=test", "SELECT 1", psql=psql)

        expect(RuntimeError, surfit.read_postgis,
               "dbname=test", "SELECT 1", psql="psql-that-does-not-exist")

        surfit.clear_data()
        print("PASS: bad column count, NULL and empty results raise")
        print("PASS: a missing psql raises instead of loading nothing")

        # Through a Session the call must install that task's state first.
        task = surfit.Session("db_task")
        with tempfile.TemporaryDirectory() as third:
            psql, _ = make_psql(third, "7,8,9\n")
            assert task.read_postgis("dbname=test", "SELECT 1", name="s",
                                     psql=psql) == [True]
            assert task.pnts_size() == 1
        task.close()
        print("PASS: Session.read_postgis loads into that task")

    return 0


if __name__ == "__main__":
    sys.exit(main())
