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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        import json
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        class TestObj:
            pass
        
        obj = TestObj()
        result = assign_defaults(obj, temp_file)
        
        assert hasattr(obj, 'rgnPenResHeat')
        assert obj.rgnPenResHeat == [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
        assert isinstance(result, dict)
        assert result == test_data
    finally:
        os.unlink(temp_file)


def test_assign_item_defaults():
    """Test basic functionality of assign_item_defaults"""
    test_data = {"rgnPenResHeat": [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        import json
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        class TestObj:
            pass
        
        obj = TestObj()
        result = assign_item_defaults(obj, temp_file)
        
        assert hasattr(obj, 'rgnPenResHeat')
        assert isinstance(obj.rgnPenResHeat, Item)
        assert obj.rgnPenResHeat.value == [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
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
    config = [
        ["Test Label", "test_value", "unit", "TEXT", "test_item"]
    ]
    
    entity = Entity("test", config)
    
    assert entity.entity == "test"
    assert entity.count() == 1
    assert hasattr(entity, 'test_item')
    assert entity.test_item.value == "test_value"


def test_entity_instance_management():
    """Test Entity instance creation and retrieval"""
    config = [
        ["Test Label", "default", "", "TEXT", "test_attr"]
    ]
    
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
    config = [
        ["Test Label", "test_value", "unit", "TEXT", "test_item"]
    ]
    
    entity = Entity("testentity", config)
    
    with tempfile.NamedTemporaryFile() as temp_db:
        conn = sqlite3.connect(temp_db.name)
        entity.toSQLite(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='testentity'")
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "testentity"
        
        conn.close()