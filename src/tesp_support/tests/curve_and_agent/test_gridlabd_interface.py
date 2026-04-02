# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for gridlabd_interface.py — GridLAB-D read/write abstraction layer.

Ground truth:
  - Interface wraps an opaque connection object (FNCS/HELICS/direct API)
  - Read methods return the correct device-state dataclasses
  - Write methods accept DeviceCommand and return success/failure bool
  - Device type determines which properties are read/written
  - This is the ONLY module that directly touches GridLAB-D

Testing strategy:
  The connection object is injected, so we mock it. Each read method should
  translate raw co-sim values into the typed state dataclass. Each write
  method should translate a DeviceCommand into co-sim property writes.
"""

import pytest
from unittest.mock import MagicMock

from gridlabd_interface import GridLABDInterface
from data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    DeviceCommand,
)
from enums_and_constants import DeviceType


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def mock_connection():
    """A mock co-simulation connection object.

    In production this could be a HELICS value federate handle,
    an FNCS bridge, or a direct GridLAB-D API handle.
    The connection protocol: get_value(key) -> str, set_value(key, val).
    """
    # Default values keyed by "object_name#property"
    _store = {}

    conn = MagicMock()

    def _get(key):
        return _store.get(key, "0.0")

    def _set(key, val):
        _store[key] = val

    conn.get_value = MagicMock(side_effect=_get)
    conn.set_value = MagicMock(side_effect=_set)
    conn._store = _store  # expose for test assertions
    return conn


def _seed_hvac(conn, obj="house_1"):
    """Seed mock connection with realistic HVAC values."""
    s = conn._store
    s[f"{obj}#air_temperature"] = "73.5"
    s[f"{obj}#outdoor_temperature"] = "92.0"
    s[f"{obj}#cooling_setpoint"] = "72.0"
    s[f"{obj}#heating_setpoint"] = "68.0"
    s[f"{obj}#power_state"] = "COOL"
    s[f"{obj}#hvac_load"] = "3500.0"  # Btu/hr
    s[f"{obj}#mass_temperature"] = "73.0"
    s[f"{obj}#Ca"] = "1500.0"
    s[f"{obj}#Cm"] = "5000.0"
    s[f"{obj}#Ua"] = "500.0"
    s[f"{obj}#Hm"] = "1500.0"
    s[f"{obj}#cooling_COP"] = "3.5"
    s[f"{obj}#heating_COP"] = "3.0"
    s[f"{obj}#design_cooling_capacity"] = "36000.0"
    s[f"{obj}#design_heating_capacity"] = "36000.0"
    s[f"{obj}#solar_heatgain"] = "800.0"
    s[f"{obj}#internal_heatgain"] = "400.0"


def _seed_wh(conn, obj="waterheater_1"):
    """Seed mock connection with realistic water heater values."""
    s = conn._store
    s[f"{obj}#UTTemp"] = "132.0"
    s[f"{obj}#LTTemp"] = "128.0"
    s[f"{obj}#UTState"] = "OFF"
    s[f"{obj}#LTState"] = "OFF"
    s[f"{obj}#upper_tank_setpoint"] = "130.0"
    s[f"{obj}#WHLoad"] = "0.0"
    s[f"{obj}#tank_volume"] = "50.0"
    s[f"{obj}#tank_UA"] = "2.0"
    s[f"{obj}#heating_element_capacity"] = "4.5"
    s[f"{obj}#inlet_water_temperature"] = "60.0"
    s[f"{obj}#WDRate"] = "0.0"
    s[f"{obj}#tank_height"] = "4.0"


def _seed_ev(conn, obj="evcharger_1"):
    """Seed mock connection with realistic EV charger values."""
    s = conn._store
    s[f"{obj}#SOC"] = "0.45"
    s[f"{obj}#charge_rate"] = "7.2"
    s[f"{obj}#battery_capacity"] = "60.0"
    s[f"{obj}#max_charge_rate"] = "7.2"
    s[f"{obj}#charger_efficiency"] = "0.90"
    s[f"{obj}#vehicle_connected"] = "TRUE"


def _seed_battery(conn, obj="battery_1"):
    """Seed mock connection with realistic battery/inverter values."""
    s = conn._store
    s[f"{obj}#SOC"] = "0.60"
    s[f"{obj}#p_out"] = "-2.0"  # GLD: negative = importing = charging
    s[f"{obj}#battery_capacity"] = "13.5"
    s[f"{obj}#rated_power"] = "5.0"
    s[f"{obj}#round_trip_efficiency"] = "0.90"
    s[f"{obj}#cell_temperature"] = "28.0"
    s[f"{obj}#inverter_rated_power"] = "5.0"
    s[f"{obj}#state_of_health"] = "0.98"


@pytest.fixture
def hvac_interface(mock_connection):
    return GridLABDInterface(
        connection=mock_connection,
        object_name="house_1",
        device_type=DeviceType.HVAC_AC_ONLY,
    )


@pytest.fixture
def wh_interface(mock_connection):
    return GridLABDInterface(
        connection=mock_connection,
        object_name="waterheater_1",
        device_type=DeviceType.WATER_HEATER,
    )


@pytest.fixture
def ev_interface(mock_connection):
    return GridLABDInterface(
        connection=mock_connection,
        object_name="evcharger_1",
        device_type=DeviceType.EV_CHARGER,
    )


@pytest.fixture
def battery_interface(mock_connection):
    return GridLABDInterface(
        connection=mock_connection,
        object_name="battery_1",
        device_type=DeviceType.BATTERY,
    )


# ===================================================================
# Construction Tests
# ===================================================================


class TestGridLABDInterfaceConstruction:
    """Verify the interface stores its injected dependencies correctly."""

    def test_stores_connection(self, hvac_interface, mock_connection):
        assert hvac_interface._connection is mock_connection

    def test_stores_object_name(self, hvac_interface):
        assert hvac_interface._object_name == "house_1"

    def test_stores_device_type(self, hvac_interface):
        assert hvac_interface._device_type == DeviceType.HVAC_AC_ONLY

    def test_all_device_types_constructable(self, mock_connection):
        """Every DeviceType enum value should be accepted."""
        for dt in DeviceType:
            iface = GridLABDInterface(
                connection=mock_connection,
                object_name=f"test_{dt.name}",
                device_type=dt,
            )
            assert iface._device_type == dt


# ===================================================================
# Read Methods
# ===================================================================


class TestReadHVACState:
    """GridLABDInterface.read_hvac_state() -> HVACState."""

    def test_returns_hvac_state(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        result = hvac_interface.read_hvac_state()
        assert isinstance(result, HVACState)

    def test_indoor_temp_populated(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        state = hvac_interface.read_hvac_state()
        assert isinstance(state.indoor_air_temp, float)
        assert state.indoor_air_temp == pytest.approx(73.5)

    def test_outdoor_temp_populated(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        state = hvac_interface.read_hvac_state()
        assert isinstance(state.outdoor_air_temp, float)
        assert state.outdoor_air_temp == pytest.approx(92.0)

    def test_thermal_parameters_populated(self, hvac_interface, mock_connection):
        """UA, thermal mass, COP should all be non-zero."""
        _seed_hvac(mock_connection)
        state = hvac_interface.read_hvac_state()
        assert state.UA_envelope > 0
        assert state.cooling_COP > 0

    def test_cooling_mode_detected(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        state = hvac_interface.read_hvac_state()
        assert state.hvac_mode == "cooling"
        assert state.hvac_on is True

    def test_heating_mode_detected(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        mock_connection._store["house_1#power_state"] = "HEAT"
        state = hvac_interface.read_hvac_state()
        assert state.hvac_mode == "heating"

    def test_off_mode_detected(self, hvac_interface, mock_connection):
        _seed_hvac(mock_connection)
        mock_connection._store["house_1#power_state"] = "OFF"
        state = hvac_interface.read_hvac_state()
        assert state.hvac_mode == "off"
        assert state.hvac_on is False


class TestReadWaterHeaterState:
    """GridLABDInterface.read_water_heater_state() -> WaterHeaterState."""

    def test_returns_wh_state(self, wh_interface, mock_connection):
        _seed_wh(mock_connection)
        result = wh_interface.read_water_heater_state()
        assert isinstance(result, WaterHeaterState)

    def test_tank_temp_populated(self, wh_interface, mock_connection):
        _seed_wh(mock_connection)
        state = wh_interface.read_water_heater_state()
        assert isinstance(state.tank_temp_upper, float)
        assert isinstance(state.tank_temp_lower, float)
        assert state.tank_temp_upper == pytest.approx(132.0)
        assert state.tank_temp_lower == pytest.approx(128.0)

    def test_tank_volume_positive(self, wh_interface, mock_connection):
        _seed_wh(mock_connection)
        state = wh_interface.read_water_heater_state()
        assert state.tank_volume > 0

    def test_element_on_when_heating(self, wh_interface, mock_connection):
        _seed_wh(mock_connection)
        mock_connection._store["waterheater_1#UTState"] = "ON"
        state = wh_interface.read_water_heater_state()
        assert state.element_on is True


class TestReadEVChargerState:
    """GridLABDInterface.read_ev_charger_state() -> EVChargerState."""

    def test_returns_ev_state(self, ev_interface, mock_connection):
        _seed_ev(mock_connection)
        result = ev_interface.read_ev_charger_state()
        assert isinstance(result, EVChargerState)

    def test_soc_in_range(self, ev_interface, mock_connection):
        _seed_ev(mock_connection)
        state = ev_interface.read_ev_charger_state()
        assert 0.0 <= state.soc <= 1.0
        assert state.soc == pytest.approx(0.45)

    def test_charge_rate_non_negative(self, ev_interface, mock_connection):
        _seed_ev(mock_connection)
        state = ev_interface.read_ev_charger_state()
        assert state.charge_rate >= 0.0

    def test_vehicle_plugged_in(self, ev_interface, mock_connection):
        _seed_ev(mock_connection)
        state = ev_interface.read_ev_charger_state()
        assert state.vehicle_plugged_in is True


class TestReadBatteryState:
    """GridLABDInterface.read_battery_state() -> BatteryState."""

    def test_returns_battery_state(self, battery_interface, mock_connection):
        _seed_battery(mock_connection)
        result = battery_interface.read_battery_state()
        assert isinstance(result, BatteryState)

    def test_soc_in_range(self, battery_interface, mock_connection):
        _seed_battery(mock_connection)
        state = battery_interface.read_battery_state()
        assert 0.0 <= state.soc <= 1.0
        assert state.soc == pytest.approx(0.60)

    def test_capacity_positive(self, battery_interface, mock_connection):
        _seed_battery(mock_connection)
        state = battery_interface.read_battery_state()
        assert state.energy_capacity > 0

    def test_sign_convention(self, battery_interface, mock_connection):
        """GLD p_out=-2 (importing/charging) → agent power=+2 (charging)."""
        _seed_battery(mock_connection)
        state = battery_interface.read_battery_state()
        assert state.power == pytest.approx(2.0)


class TestReadSimulationTime:
    """GridLABDInterface.read_simulation_time() -> float."""

    def test_returns_float(self, hvac_interface, mock_connection):
        mock_connection._store["house_1#clock"] = "1709712000.0"
        result = hvac_interface.read_simulation_time()
        assert isinstance(result, float)
        assert result == pytest.approx(1709712000.0)


# ===================================================================
# Write Methods
# ===================================================================


def _make_command(device_type, setpoint=72.0, mode="", power_target=0.0):
    return DeviceCommand(
        device_type=device_type,
        setpoint=setpoint,
        mode=mode,
        power_target=power_target,
    )


class TestWriteHVACCommand:
    """GridLABDInterface.write_hvac_command(DeviceCommand) -> bool."""

    def test_returns_bool(self, hvac_interface, mock_connection):
        cmd = _make_command(DeviceType.HVAC_AC_ONLY, setpoint=74.0, mode="cooling")
        result = hvac_interface.write_hvac_command(cmd)
        assert isinstance(result, bool)

    def test_cooling_setpoint_write(self, hvac_interface, mock_connection):
        """Writing a cooling command should push the setpoint to GridLAB-D."""
        cmd = _make_command(DeviceType.HVAC_AC_ONLY, setpoint=76.0, mode="cooling")
        hvac_interface.write_hvac_command(cmd)
        assert "house_1#cooling_setpoint" in mock_connection._store
        assert mock_connection._store["house_1#cooling_setpoint"] == 76.0

    def test_heating_setpoint_write(self, hvac_interface, mock_connection):
        cmd = _make_command(DeviceType.HVAC_AC_ONLY, setpoint=68.0, mode="heating")
        result = hvac_interface.write_hvac_command(cmd)
        assert result is True
        assert "house_1#heating_setpoint" in mock_connection._store
        assert mock_connection._store["house_1#heating_setpoint"] == 68.0


class TestWriteWaterHeaterCommand:
    """GridLABDInterface.write_water_heater_command(DeviceCommand) -> bool."""

    def test_returns_bool(self, wh_interface, mock_connection):
        cmd = _make_command(DeviceType.WATER_HEATER, setpoint=135.0)
        result = wh_interface.write_water_heater_command(cmd)
        assert isinstance(result, bool)

    def test_setpoint_write(self, wh_interface, mock_connection):
        cmd = _make_command(DeviceType.WATER_HEATER, setpoint=140.0)
        wh_interface.write_water_heater_command(cmd)
        assert "waterheater_1#upper_tank_setpoint" in mock_connection._store
        assert mock_connection._store["waterheater_1#upper_tank_setpoint"] == 140.0


class TestWriteEVChargerCommand:
    """GridLABDInterface.write_ev_charger_command(DeviceCommand) -> bool."""

    def test_returns_bool(self, ev_interface, mock_connection):
        cmd = _make_command(DeviceType.EV_CHARGER, power_target=7.2)
        result = ev_interface.write_ev_charger_command(cmd)
        assert isinstance(result, bool)

    def test_charge_rate_write(self, ev_interface, mock_connection):
        cmd = _make_command(DeviceType.EV_CHARGER, power_target=3.6)
        ev_interface.write_ev_charger_command(cmd)
        assert "evcharger_1#charge_rate" in mock_connection._store
        assert mock_connection._store["evcharger_1#charge_rate"] == 3.6


class TestWriteBatteryCommand:
    """GridLABDInterface.write_battery_command(DeviceCommand) -> bool."""

    def test_returns_bool(self, battery_interface, mock_connection):
        cmd = _make_command(DeviceType.BATTERY, power_target=3.0)
        result = battery_interface.write_battery_command(cmd)
        assert isinstance(result, bool)

    def test_discharge_command(self, battery_interface, mock_connection):
        """Negative power_target means discharge (export to grid)."""
        cmd = _make_command(DeviceType.BATTERY, power_target=-5.0)
        battery_interface.write_battery_command(cmd)
        assert "battery_1#p_out" in mock_connection._store
        # Agent -5 (discharge) → GLD +5 (export)
        assert mock_connection._store["battery_1#p_out"] == pytest.approx(5.0)

    def test_sign_convention_handled(self, battery_interface, mock_connection):
        """Agent convention: positive=charge. GridLAB-D: positive=export.
        The interface must convert."""
        cmd = _make_command(DeviceType.BATTERY, power_target=3.0)
        result = battery_interface.write_battery_command(cmd)
        assert result is True
        # Agent +3 (charge) → GLD -3 (import)
        assert mock_connection._store["battery_1#p_out"] == pytest.approx(-3.0)
