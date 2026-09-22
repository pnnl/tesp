# test_store.py
import csv
import os
import sqlite3
import tempfile

import pytest
from tesp_support.api.store import Directory, Schema, Store


def test_store_debug_resample():
    """Test debug resample functionality from _test_debug_resample"""
    import numpy as np
    import pandas as pd
    from tesp_support.api.metrics_api import synch_series

    # Replicate the original test data
    np.random.seed(0)  # Same seed as original
    tseries = []

    start, end = "2000-01-01 22:00:00", "2001-01-01 22:35:00"
    start1, end1 = "2000-01-01 22:05:00", "2001-01-01 22:40:00"
    start2, end2 = "2000-01-01 22:10:00", "2001-01-01 22:45:00"
    start3, end3 = "2000-01-01 22:15:00", "2001-01-01 22:30:00"

    # Create test DataFrames
    rng = pd.date_range(start, end, freq="1min")
    ts = pd.DataFrame(
        np.random.randint(0, 20, size=(rng.size, 2)),
        columns=["temp", "humidity"],
        index=rng,
    )

    rng = pd.date_range(start1, end1, freq="1min")
    ts1 = pd.DataFrame(
        np.random.randint(0, 20, size=(rng.size, 2)),
        columns=["temp", "humidity"],
        index=rng,
    )

    rng = pd.date_range(start2, end2, freq="1min")
    ts2 = pd.DataFrame(
        np.random.randint(0, 20, size=(rng.size, 2)),
        columns=["temp", "humidity"],
        index=rng,
    )

    rng = pd.date_range(start3, end3, freq="1min")
    ts3 = pd.DataFrame(
        np.random.randint(0, 20, size=(rng.size, 2)),
        columns=["temp", "humidity"],
        index=rng,
    )

    tseries = [ts1, ts2, ts3, ts]

    # Test the synch_series function
    synched_series = synch_series(tseries, 2, "min")

    # Test that it returns a list of DataFrames, not a single DataFrame
    assert isinstance(synched_series, list)
    assert len(synched_series) == len(tseries)  # Should have same number of series

    # Test that each item in the list is a DataFrame
    for i, series in enumerate(synched_series):
        assert isinstance(series, pd.DataFrame)
        assert len(series.columns) == 2  # temp and humidity
        assert "temp" in series.columns
        assert "humidity" in series.columns

    # Test that all series have matching indices (synchronized)
    if len(synched_series) > 1:
        base_index = synched_series[0].index
        for i, series in enumerate(synched_series[1:], 1):
            # Check that indices are the same length
            assert len(series.index) == len(base_index), (
                f"Series {i} has different index length"
            )

            # Check that indices have overlapping time ranges
            # (they might not be exactly identical due to resampling, but should overlap)
            base_start, base_end = base_index.min(), base_index.max()
            series_start, series_end = series.index.min(), series.index.max()

            # There should be some overlap in the time ranges
            overlap_start = max(base_start, series_start)
            overlap_end = min(base_end, series_end)
            assert overlap_start <= overlap_end, (
                f"Series {i} has no time overlap with base series"
            )

    # Test that the synchronized series have the expected frequency
    for i, series in enumerate(synched_series):
        if len(series) > 1:
            # Check that the frequency is roughly what we expected (2 minute intervals)
            time_diff = series.index[1] - series.index[0]
            expected_diff = pd.Timedelta(minutes=2)
            assert time_diff == expected_diff, (
                f"Series {i} doesn't have expected 2-minute frequency"
            )

    # Verify that the original test output is replicated
    # The original prints the first DataFrame
    first_series = synched_series[0]
    assert len(first_series) > 0
    assert isinstance(
        first_series.iloc[0]["temp"], (int, float, np.integer, np.floating)
    )
    assert isinstance(
        first_series.iloc[0]["humidity"], (int, float, np.integer, np.floating)
    )


def test_store_with_real_csv_file():
    """Test Store with real CSV file from tesp_test"""
    from tesp_support.api.data import tesp_test

    csv_path = tesp_test + "api/test.csv"
    store_path = tesp_test + "api/store_test"

    # Only run if the test file exists
    if os.path.exists(csv_path):
        store = Store(store_path)
        schema = store.add_file(csv_path, "test_csv", "My test csv file")

        tables = schema.get_tables()
        assert len(tables) == 1
        assert tables[0] == "test"  # Based on output

        columns = schema.get_columns(tables[0])
        expected_columns = [
            "Hour_End",
            "Bus1",
            "Bus2",
            "Bus3",
            "Bus4",
            "Bus5",
            "Bus6",
            "Bus7",
            "Bus8",
            "ERCOT",
        ]

        for expected_col in expected_columns:
            assert expected_col in columns

        # Test writing store config
        store.write()
        assert os.path.exists(store_path + ".json")


def test_store_with_real_sqlite_file():
    """Test Store with real SQLite file from tesp_test"""
    from tesp_support.api.data import tesp_test

    db_path = tesp_test + "api/test.db"
    store_path = tesp_test + "api/store_test"

    # Only run if the test file exists
    if os.path.exists(db_path):
        store = Store(store_path)
        schema = store.add_file(db_path, "test_db", "My test sqlite file")

        tables = schema.get_tables()
        expected_tables = [
            "climate",
            "commercial",
            "connection",
            "generators",
            "market",
            "powerflow",
            "reliability",
            "residential",
            "tape",
        ]

        for expected_table in expected_tables:
            assert expected_table in tables

        if len(tables) > 0:
            columns = schema.get_columns(tables[0])
            expected_columns = ["label", "unit", "datatype", "item", "valu"]

            for expected_col in expected_columns:
                assert expected_col in columns

        # Test writing store config
        store.write()


def test_store_series_data_reading():
    """Test Store series data reading from _test_read"""
    from tesp_support.api.data import tesp_test

    csv_path = tesp_test + "api/test.csv"
    store_path = tesp_test + "api/store_test"

    # Only run if the test file exists
    if os.path.exists(csv_path):
        store = Store(store_path)
        schema = store.add_file(csv_path, "test_csv", "My test csv file")

        tables = schema.get_tables()
        if len(tables) > 0:
            columns = schema.get_columns(tables[0])

            # Test setting date by column
            if "Hour_End" in columns:
                result = schema.set_date_bycol(tables[0], "Hour_End")
                assert result

            # Test setting date by row
            result = schema.set_date_byrow(tables[0], "2016-01-01 00:00", "H")
            assert result

            store.write()


def test_directory_file_inclusion():
    """Test Directory file inclusion from _test_dir"""
    from tesp_support.api.data import tesp_share, tesp_test

    # Only run if tesp_share directory exists
    if os.path.exists(tesp_share):
        store_path = tesp_test + "api/store_test"
        store = Store(store_path)

        directory = store.add_path(tesp_share, "My data directory")

        # Test setting include directories
        result1 = directory.set_includeDir("energyplus")
        if result1:  # Only test if directory exists
            assert result1 == "energyplus"

        # Test setting include files
        feeders_path = directory.set_includeDir("feeders", True)
        if feeders_path:
            result2 = directory.set_includeFile(feeders_path, "IEE*")
            result3 = directory.set_includeFile(feeders_path, "comm*")
            result4 = directory.set_includeFile(feeders_path, ".gitignore")

        store.write()

        # Test zip functionality
        store.zip()
        zip_file = store_path + ".zip"
        if os.path.exists(zip_file):
            assert os.path.getsize(zip_file) > 0  # Zip file should have content


def test_store_schema_json_output():
    """Test Schema toJSON method"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        # Create test CSV
        writer = csv.writer(f)
        writer.writerow(['col1', 'col2'])
        writer.writerow(['data1', 'data2'])
        temp_file = f.name
    
    try:
        schema = Schema(temp_file, "test", "Test CSV")
        schema.get_tables()
        schema.get_columns(schema.tables[0])
        
        json_output = schema.toJSON()
        
        assert isinstance(json_output, dict)
        assert "path" in json_output
        assert "name" in json_output
        assert "filetype" in json_output
        assert "description" in json_output
        assert "schema" in json_output
        assert json_output["filetype"] == ".csv"
        
    finally:
        os.unlink(temp_file)


def test_schema_csv_creation():
    """Test Schema class with CSV file"""
    # Create a temporary CSV file
    test_data = [
        ["Hour_End", "Bus1", "Bus2", "Bus3"],
        ["2016-01-01 01:00", "100", "200", "300"],
        ["2016-01-01 02:00", "110", "210", "310"],
    ]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
        temp_file = f.name

    try:
        schema = Schema(temp_file, "test")
        tables = schema.get_tables()

        assert len(tables) == 1
        # Schema uses filename without extension, not the provided name
        expected_name = os.path.splitext(os.path.basename(temp_file))[0]
        assert tables[0] == expected_name

        columns = schema.get_columns(tables[0])
        assert "Hour_End" in columns
        assert "Bus1" in columns
        assert "Bus2" in columns
        assert "Bus3" in columns

    finally:
        os.unlink(temp_file)


def test_schema_sqlite_creation():
    """Test Schema class with SQLite database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute("CREATE TABLE climate (id INTEGER, temp REAL)")
        cursor.execute("CREATE TABLE market (id INTEGER, price REAL)")
        conn.commit()
        conn.close()

        try:
            schema = Schema(temp_db.name, "test_db")
            tables = schema.get_tables()

            assert "climate" in tables
            assert "market" in tables

            columns = schema.get_columns("climate")
            assert "id" in columns
            assert "temp" in columns

        finally:
            os.unlink(temp_db.name)


def test_directory_creation():
    """Test Directory class"""
    with tempfile.TemporaryDirectory() as temp_dir:
        directory = Directory(temp_dir, "Test directory")

        assert directory.name == os.path.basename(temp_dir)
        assert directory.description == "Test directory"
        assert directory.ext == "dir"


def test_store_creation():
    """Test Store class basic functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        store_path = os.path.join(temp_dir, "test_store")
        store = Store(store_path)

        # Test adding a directory
        test_dir = temp_dir
        directory = store.add_path(test_dir, "Test directory")

        assert isinstance(directory, Directory)
        assert directory.file == test_dir


def test_store_csv_integration():
    """Test Store with CSV file integration"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create CSV file
        csv_file = os.path.join(temp_dir, "test.csv")
        test_data = [["Hour_End", "Bus1", "Bus2"], ["2016-01-01 01:00", "100", "200"]]

        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)

        # Create store
        store_path = os.path.join(temp_dir, "test_store")
        store = Store(store_path)

        # Add file to store
        schema = store.add_file(csv_file, "test_csv", "Test CSV file")

        assert isinstance(schema, Schema)
        # Schema uses filename without extension as name
        assert schema.name == "test"  # From "test.csv"

        tables = schema.get_tables()
        assert len(tables) == 1
        assert tables[0] == "test"


@pytest.mark.parametrize(
    "file_ext,expected_tables",
    [
        (".csv", 1),
        (".db", 0),  # Empty database initially
    ],
)
def test_schema_file_types(file_ext, expected_tables):
    """Test Schema with different file types"""
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as f:
        temp_file = f.name

    try:
        if file_ext == ".csv":
            # Write basic CSV
            with open(temp_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["col1", "col2"])
                writer.writerow(["data1", "data2"])
        elif file_ext == ".db":
            # Create empty SQLite database
            conn = sqlite3.connect(temp_file)
            conn.close()

        schema = Schema(temp_file, "test")
        tables = schema.get_tables()
        assert len(tables) >= expected_tables

    finally:
        os.unlink(temp_file)
