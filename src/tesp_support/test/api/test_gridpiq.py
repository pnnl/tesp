# test_gridpiq.py
import pytest
import tempfile
import json
from datetime import datetime, timedelta
from tesp_support.api.gridpiq import GridPIQ


def test_gridpiq_creation():
    """Test GridPIQ class initialization"""
    piq = GridPIQ()
    
    assert piq.max_load == 0
    assert isinstance(piq.Nuclear, list)
    assert isinstance(piq.Wind, list)
    assert isinstance(piq.Coal, list)
    assert isinstance(piq.Solar, list)
    assert isinstance(piq.NaturalGas, list)
    assert isinstance(piq.Petroleum, list)
    assert len(piq.Nuclear) == 0
    assert len(piq.Wind) == 0


def test_set_dispatch_data():
    """Test setting dispatch data"""
    piq = GridPIQ()
    
    # Test adding data to different sources
    piq.set_dispatch_data("Nuclear", 0, 100.0)
    piq.set_dispatch_data("Wind", 0, 50.0)
    piq.set_dispatch_data("coal", 0, 200.0)  # Test lowercase
    
    assert len(piq.Nuclear) == 1
    assert piq.Nuclear[0] == 100.0
    assert len(piq.Wind) == 1
    assert piq.Wind[0] == 50.0
    assert len(piq.Coal) == 1
    assert piq.Coal[0] == 200.0


def test_set_dispatch_data_multiple_indices():
    """Test setting dispatch data at different indices"""
    piq = GridPIQ()
    
    piq.set_dispatch_data("Nuclear", 0, 100.0)
    piq.set_dispatch_data("Nuclear", 2, 300.0)  # Skip index 1
    
    assert len(piq.Nuclear) == 3
    assert piq.Nuclear[0] == 100.0
    assert piq.Nuclear[1] == 0  # Filled with zeros
    assert piq.Nuclear[2] == 300.0


def test_avg_dispatch_data():
    """Test averaging dispatch data"""
    piq = GridPIQ()
    
    piq.set_dispatch_data("Nuclear", 0, 900.0)
    piq.avg_dispatch_data(9)  # Average by 9 (like the test does)
    
    assert piq.Nuclear[0] == 100.0  # 900/9 = 100


def test_set_max_load():
    """Test setting maximum load"""
    piq = GridPIQ()
    
    assert piq.max_load == 0
    
    piq.set_max_load(1000.0)
    assert piq.max_load == 1000.0
    
    piq.set_max_load(500.0)  # Lower value shouldn't change max
    assert piq.max_load == 1000.0
    
    piq.set_max_load(1500.0)  # Higher value should change max
    assert piq.max_load == 1500.0


def test_set_datetime():
    """Test setting datetime ranges"""
    piq = GridPIQ()
    
    start_date = "2016-01-03 00:00:00"
    end_date = "2016-01-05 00:00:00"
    
    piq.set_datetime(start_date, end_date, 24, -1)
    
    # Verify that datetime fields were set (basic check)
    assert piq.tech is not None
    assert piq.context is not None


def test_reset_dispatch_data():
    """Test resetting dispatch data"""
    piq = GridPIQ()
    
    # Add some data
    piq.set_dispatch_data("Nuclear", 0, 100.0)
    piq.set_dispatch_data("Wind", 0, 50.0)
    
    assert len(piq.Nuclear) == 1
    assert len(piq.Wind) == 1
    
    # Reset should clear the data
    piq.reset_dispatch_data()
    
    assert len(piq.Zeros) == 0
    assert len(piq.Total) == 0


def test_tojson_basic():
    """Test basic JSON generation"""
    piq = GridPIQ()
    
    # Add minimal data
    piq.set_dispatch_data("Nuclear", 0, 100.0)
    piq.set_dispatch_data("Wind", 0, 50.0)
    piq.set_max_load(200.0)
    
    result = piq.toJson()
    
    assert isinstance(result, dict)
    assert "tech" in result
    assert "impacts" in result
    assert "context" in result
    assert "global" in result


def test_write_file():
    """Test writing JSON to file"""
    piq = GridPIQ()
    
    # Add minimal data
    piq.set_dispatch_data("Nuclear", 0, 100.0)
    piq.set_max_load(100.0)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        piq.write(temp_file)
        
        # Verify file was written and contains valid JSON
        with open(temp_file, 'r') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert "tech" in data
        
    finally:
        import os
        os.unlink(temp_file)


@pytest.mark.parametrize("fuel_type,expected_attr", [
    ("Nuclear", "Nuclear"),
    ("nuclear", "Nuclear"),
    ("Wind", "Wind"),
    ("wind", "Wind"),
    ("Coal", "Coal"),
    ("coal", "Coal"),
    ("Solar", "Solar"),
    ("solar", "Solar"),
    ("NaturalGas", "NaturalGas"),
    ("naturalgas", "NaturalGas"),
    ("Petroleum", "Petroleum"),
    ("petroleum", "Petroleum"),
])
def test_fuel_type_mapping(fuel_type, expected_attr):
    """Test that fuel types map correctly to attributes"""
    piq = GridPIQ()
    
    piq.set_dispatch_data(fuel_type, 0, 100.0)
    
    attr_list = getattr(piq, expected_attr)
    assert len(attr_list) == 1
    assert attr_list[0] == 100.0