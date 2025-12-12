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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_file = f.name

    try:
        piq.write(temp_file)

        # Verify file was written and contains valid JSON
        with open(temp_file, "r") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "tech" in data

    finally:
        import os

        os.unlink(temp_file)


@pytest.mark.parametrize(
    "fuel_type,expected_attr",
    [
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
    ],
)
def test_fuel_type_mapping(fuel_type, expected_attr):
    """Test that fuel types map correctly to attributes"""
    piq = GridPIQ()

    piq.set_dispatch_data(fuel_type, 0, 100.0)

    attr_list = getattr(piq, expected_attr)
    assert len(attr_list) == 1
    assert attr_list[0] == 100.0


def test_gridpiq_full_workflow_from_original_test():
    """Test complete GridPIQ workflow replicating the original _test() function"""
    start_date = "2016-01-03 00:00:00"
    end_date = "2016-01-05 00:00:00"
    choices = ["Nuclear", "Wind", "Coal", "Solar", "NaturalGas", "Petroleum"]
    percent = [0.10, 0.10, 0.40, 0.0, 0.30, 0.10]
    data = [
        44549.86877,
        45016.21691,
        47017.04049,
        45582.91460,
        46028.10423,
        46489.12242,
        46846.10710,
        46890.73556,
        46086.56812,
        44254.71294,
        42134.03615,
        40375.42948,
        39034.53516,
        38206.21089,
        37822.15485,
        37919.82094,
        38486.89171,
        39637.39861,
        41622.17184,
        43177.01046,
        43815.28902,
        44178.21888,
        42964.65054,
        42026.75463,
    ]

    piq = GridPIQ()
    piq.set_datetime(start_date, end_date, 24, -1)

    # Replicate the exact workflow from _test()
    for j in range(len(data)):
        for i in range(len(choices)):
            if i != 3:  # Skip Solar (index 3, 0% in original)
                # Add data 9 times (like original test)
                for k in range(8):
                    piq.set_dispatch_data(choices[i], j, data[j] * percent[i])
                # Add one more time outside the loop (total of 9)
                piq.set_dispatch_data(choices[i], j, data[j] * percent[i])
        piq.avg_dispatch_data(9)  # Average by 9 samples

    piq.set_max_load(55678.4353)  # Same max load as original

    # Validate the data was set correctly
    assert len(piq.Nuclear) == 24
    assert len(piq.Wind) == 24
    assert len(piq.Coal) == 24
    assert len(piq.Solar) == 0  # Solar should be empty (0%)
    assert len(piq.NaturalGas) == 24
    assert len(piq.Petroleum) == 24

    # Test that percentages are correct (approximately)
    for j in range(24):
        expected_nuclear = data[j] * 0.10
        expected_coal = data[j] * 0.40
        expected_gas = data[j] * 0.30

        assert abs(piq.Nuclear[j] - expected_nuclear) < 1e-6
        assert abs(piq.Coal[j] - expected_coal) < 1e-6
        assert abs(piq.NaturalGas[j] - expected_gas) < 1e-6

    # Test max load
    assert piq.max_load == 55678.4353

    # Test JSON generation
    result = piq.toJson()

    # Validate JSON structure matches AVERT requirements
    assert isinstance(result, dict)
    required_keys = ["tech", "impacts", "context", "global"]
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"

    # Test that dispatch data was normalized to percentages
    context_dispatch = result["context"]["parameters"]["dispatch_data"]["data"]

    # Should have data for all fuel types except Solar
    expected_fuels = ["Nuclear", "Wind", "Coal", "Natural Gas", "Petroleum"]
    for fuel in expected_fuels:
        if fuel != "Solar":  # Solar should be missing since it's 0%
            assert fuel in context_dispatch
            fuel_data = context_dispatch[fuel]
            assert len(fuel_data) == 24

            # Each value should be a percentage (between 0 and 1)
            for value in fuel_data:
                assert 0 <= value <= 1, f"Percentage out of range: {value}"

    # Test that percentages sum to 1.0 for each hour
    for j in range(24):
        total_percent = 0
        for fuel in expected_fuels:
            if fuel in context_dispatch:
                total_percent += context_dispatch[fuel][j]
        assert abs(total_percent - 1.0) < 1e-10, (
            f"Percentages don't sum to 1.0 at hour {j}: {total_percent}"
        )


def test_gridpiq_json_structure_validation():
    """Test that JSON output has correct AVERT structure"""
    piq = GridPIQ()

    # Add minimal test data
    test_data = [100, 200, 300]
    for j, load in enumerate(test_data):
        piq.set_dispatch_data("Nuclear", j, load * 0.5)
        piq.set_dispatch_data("Coal", j, load * 0.5)

    piq.set_max_load(300)

    result = piq.toJson()

    # Test top-level structure
    assert "tech" in result
    assert "impacts" in result
    assert "context" in result
    assert "global" in result

    # Test tech section
    assert isinstance(result["tech"], list)
    assert len(result["tech"]) == 1
    tech = result["tech"][0]
    assert "parameters" in tech
    assert "post_project_load" in tech["parameters"]
    assert "post_project_max_load" in tech["parameters"]

    # Test context section
    context = result["context"]
    assert "parameters" in context
    context_params = context["parameters"]
    assert "pre_project_load" in context_params
    assert "pre_project_max_load" in context_params
    assert "dispatch_data" in context_params

    # Test dispatch data structure
    dispatch_data = context_params["dispatch_data"]["data"]
    assert isinstance(dispatch_data, dict)

    # Should have normalized percentages
    for fuel_type, fuel_data in dispatch_data.items():
        assert isinstance(fuel_data, list)
        for percentage in fuel_data:
            assert 0 <= percentage <= 1


def test_gridpiq_percentage_normalization():
    """Test that toJson() properly normalizes dispatch data to percentages"""
    piq = GridPIQ()

    # Set known values that should normalize to specific percentages
    piq.set_dispatch_data("Nuclear", 0, 100)  # Should be 25% (100/400)
    piq.set_dispatch_data("Coal", 0, 300)  # Should be 75% (300/400)
    # Total = 400

    piq.set_dispatch_data("Nuclear", 1, 200)  # Should be 50% (200/400)
    piq.set_dispatch_data("Wind", 1, 200)  # Should be 50% (200/400)
    # Total = 400

    result = piq.toJson()
    dispatch_data = result["context"]["parameters"]["dispatch_data"]["data"]

    # Check first time step
    assert abs(dispatch_data["Nuclear"][0] - 0.25) < 1e-10  # 100/400 = 0.25
    assert abs(dispatch_data["Coal"][0] - 0.75) < 1e-10  # 300/400 = 0.75

    # Check second time step
    assert abs(dispatch_data["Nuclear"][1] - 0.5) < 1e-10  # 200/400 = 0.5
    assert abs(dispatch_data["Wind"][1] - 0.5) < 1e-10  # 200/400 = 0.5
