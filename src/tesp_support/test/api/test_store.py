# test_store.py
import pytest
import tempfile
import os
import csv
import sqlite3
import pandas as pd
from tesp_support.api.store import Schema, Directory, Store


def test_schema_csv_creation():
    """Test Schema class with CSV file"""
    # Create a temporary CSV file
    test_data = [
        ['Hour_End', 'Bus1', 'Bus2', 'Bus3'],
        ['2016-01-01 01:00', '100', '200', '300'],
        ['2016-01-01 02:00', '110', '210', '310']
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
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
        assert 'Hour_End' in columns
        assert 'Bus1' in columns
        assert 'Bus2' in columns
        assert 'Bus3' in columns
        
    finally:
        os.unlink(temp_file)


def test_schema_sqlite_creation():
    """Test Schema class with SQLite database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
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
        test_data = [
            ['Hour_End', 'Bus1', 'Bus2'],
            ['2016-01-01 01:00', '100', '200']
        ]
        
        with open(csv_file, 'w', newline='') as f:
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


@pytest.mark.parametrize("file_ext,expected_tables", [
    (".csv", 1),
    (".db", 0),  # Empty database initially
])
def test_schema_file_types(file_ext, expected_tables):
    """Test Schema with different file types"""
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as f:
        temp_file = f.name
    
    try:
        if file_ext == ".csv":
            # Write basic CSV
            with open(temp_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['col1', 'col2'])
                writer.writerow(['data1', 'data2'])
        elif file_ext == ".db":
            # Create empty SQLite database
            conn = sqlite3.connect(temp_file)
            conn.close()
        
        schema = Schema(temp_file, "test")
        tables = schema.get_tables()
        assert len(tables) >= expected_tables
        
    finally:
        os.unlink(temp_file)