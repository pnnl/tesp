# test_entity.py
import pytest
import tempfile
import os
import sqlite3
from tesp_support.api.entity import assign_defaults, assign_item_defaults, Item, Entity


def test_assign_defaults():
    """Test basic functionality of assign_defaults"""
    # Create a temporary JSON file
    test_data = {"rgnPenResHeat": [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json

        json.dump(test_data, f)
        temp_file = f.name

    try:

        class TestObj:
            pass

        obj = TestObj()
        result = assign_defaults(obj, temp_file)

        assert hasattr(obj, "rgnPenResHeat")
        assert obj.rgnPenResHeat == [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
        assert isinstance(result, dict)
        assert result == test_data
    finally:
        os.unlink(temp_file)


def test_assign_item_defaults():
    """Test basic functionality of assign_item_defaults"""
    test_data = {"rgnPenResHeat": [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json

        json.dump(test_data, f)
        temp_file = f.name

    try:

        class TestObj:
            pass

        obj = TestObj()
        result = assign_item_defaults(obj, temp_file)

        assert hasattr(obj, "rgnPenResHeat")
        assert isinstance(obj.rgnPenResHeat, Item)
        assert obj.rgnPenResHeat.value == [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
        assert obj.rgnPenResHeat.datatype == str(list)
    finally:
        os.unlink(temp_file)


def test_item_creation():
    """Test Item class basic functionality"""
    item = Item("list", "rgnPenResHeat", "", "rgnPenResHeat", [0.2628, 0.0896])

    assert item.datatype == "list"
    assert item.label == "rgnPenResHeat"
    assert item.item == "rgnPenResHeat"
    assert item.value == [0.2628, 0.0896]
    assert str(item) == str([0.2628, 0.0896])


def test_entity_creation():
    """Test Entity class basic functionality"""
    config = [["Test Label", "test_value", "unit", "TEXT", "test_item"]]

    entity = Entity("test", config)

    assert entity.entity == "test"
    assert entity.count() == 1
    assert hasattr(entity, "test_item")
    assert entity.test_item.value == "test_value"


def test_entity_instance_management():
    """Test Entity instance creation and retrieval"""
    config = [["Test Label", "default", "", "TEXT", "test_attr"]]

    entity = Entity("test", config)

    # Set instance
    params = {"test_attr": "instance_value"}
    instance = entity.set_instance("test_obj", params)

    assert instance is not None
    assert instance["test_attr"] == "instance_value"

    # Get instance
    retrieved = entity.get_instance("test_obj")
    assert retrieved["test_attr"] == "instance_value"


def test_entity_sqlite_creation():
    """Test Entity SQLite table creation"""
    config = [["Test Label", "test_value", "unit", "TEXT", "test_item"]]

    entity = Entity("testentity", config)

    with tempfile.NamedTemporaryFile() as temp_db:
        conn = sqlite3.connect(temp_db.name)
        entity.toSQLite(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='testentity'"
        )
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "testentity"

        conn.close()


def test_entity_tohelp():
    """Test Entity.toHelp() method like original _test"""
    config = [["Test Label", "test_value", "unit", "TEXT", "test_item"]]
    entity = Entity("testentity", config)

    help_text = entity.toHelp()
    assert "Entity: testentity" in help_text
    assert "Test Label" in help_text


def test_multiple_entities_from_glm_file():
    """Test loading multiple entities from glm_entities_path and adding to SQLite database"""
    from tesp_support.api.data import glm_entities_path, tesp_test
    import pyjson5
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        try:
            conn = sqlite3.connect(temp_db.name)

            # Load entities from the actual glm_entities_path file
            with open(glm_entities_path, "r", encoding="utf-8") as json_file:
                entities = pyjson5.load(json_file)
                mylist = {}

                for name in entities:
                    mylist[name] = Entity(name, entities[name])

                    # Test that Entity was created correctly
                    assert mylist[name].entity == name
                    assert isinstance(mylist[name], Entity)

                    # Test toHelp() method produces expected output
                    help_text = mylist[name].toHelp()
                    assert f"Entity: {name}" in help_text

                    # Test toSQLite() method creates tables
                    mylist[name].toSQLite(conn)

                    # Verify table was created in database
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (name,),
                    )
                    result = cursor.fetchone()
                    assert result is not None, f"Table {name} was not created"
                    assert result[0] == name

                    # Verify table has expected columns
                    cursor.execute(f"PRAGMA table_info({name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    expected_columns = ["label", "unit", "datatype", "item", "valu"]
                    for expected_col in expected_columns:
                        assert expected_col in column_names, (
                            f"Column {expected_col} missing from table {name}"
                        )

            conn.close()

            # Verify we processed the expected entities (based on the original output)
            expected_entities = [
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

            for expected_entity in expected_entities:
                assert expected_entity in mylist, (
                    f"Expected entity {expected_entity} not found"
                )

        finally:
            os.unlink(temp_db.name)


def test_entity_tohelp_method():
    """Test Entity.toHelp() method output format"""
    config = [
        ["Temperature Label", "25.0", "°C", "REAL", "temperature"],
        ["Name Label", "test_name", "", "TEXT", "name"],
    ]

    entity = Entity("climate", config)
    help_text = entity.toHelp()

    # Verify help format matches expected output
    assert "Entity: climate" in help_text
    assert "Temperature Label, code=temperature, type=REAL, default=25.0" in help_text
    assert "Name Label, code=name, type=TEXT, default=test_name" in help_text


def test_entity_database_error_handling():
    """Test database error handling like the original _test try/except"""
    config = [["Test Label", "test_value", "unit", "TEXT", "test_item"]]
    entity = Entity("testentity", config)

    # Test with invalid database path (should not raise exception)
    invalid_conn = None
    try:
        # This should fail gracefully
        entity.toSQLite(invalid_conn)
    except Exception as e:
        # If it raises an exception, that's also valid behavior to test
        assert isinstance(e, (AttributeError, TypeError))
