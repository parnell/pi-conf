from unittest.mock import Mock, patch

import pytest
from bson import ObjectId
from pydantic import BaseModel
from pymongo.errors import ServerSelectionTimeoutError

from pi_conf.config_settings import ConfigDict, ConfigSettings, MongoConfigSource


class SubConfig(BaseModel):
    value: int


class TestConfig(ConfigSettings):
    string_value: str
    int_value: int
    nested_config: SubConfig

    model_config = ConfigDict()


class MockCursor:
    def __init__(self, documents):
        self.documents = documents

    def __iter__(self):
        return iter(self.documents)


class MockCollection:
    def __init__(self, documents):
        self.documents = documents

    def find_one(self, query):
        return self.documents[0] if self.documents else None

    def find(self, query):
        return MockCursor(self.documents)


class MockDatabase:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return self.collections.get(name, MockCollection([]))


class MockMongoClient:
    def __init__(self, databases):
        self.databases = databases

    def __getitem__(self, name):
        return self.databases.get(name, MockDatabase({}))

    def close(self):
        pass


@pytest.fixture
def mock_mongo():
    test_document = {
        "_id": ObjectId(),
        "string_value": "test_string",
        "int_value": 42,
        "nested_config": {"value": 10},
    }
    return MockMongoClient(
        {"test_db": MockDatabase({"test_collection": MockCollection([test_document])})}
    )


@patch("pi_conf.config_settings.MongoClient")
def test_mongo_config_source(MockClient, mock_mongo):
    MockClient.return_value = mock_mongo

    config_source = MongoConfigSource(
        mongo_uri="mongodb://localhost:27017",
        mongo_database="test_db",
        mongo_collection="test_collection",
        mongo_query={"string_value": "test_string"},
    )
    config = config_source.load_config()

    assert isinstance(config, dict)
    assert config["string_value"] == "test_string"
    assert config["int_value"] == 42
    assert config["nested_config"]["value"] == 10


@patch("pi_conf.config_settings.MongoClient")
def test_config_settings_with_mongo(MockClient, mock_mongo):
    MockClient.return_value = mock_mongo

    mongo_uri = "mongodb://localhost:27017"
    db_name = "test_db"
    collection_name = "test_collection"

    class MongoTestConfig(TestConfig):
        model_config = ConfigDict(
            mongo_uri=mongo_uri, mongo_database=db_name, mongo_collection=collection_name
        )

    config = MongoTestConfig(
        string_value="default_string", int_value=42, nested_config={"value": 10}  # type: ignore
    )

    assert config.string_value == "default_string"
    assert config.int_value == 42
    assert isinstance(config.nested_config, SubConfig)
    assert config.nested_config.value == 10


@patch("pi_conf.config_settings.MongoClient")
def test_mongo_config_source_empty_collection(MockClient):
    mock_mongo = MockMongoClient({"test_db": MockDatabase({"test_collection": MockCollection([])})})
    MockClient.return_value = mock_mongo

    config_source = MongoConfigSource(
        mongo_uri="mongodb://localhost:27017",
        mongo_database="test_db",
        mongo_collection="test_collection",
        mongo_query={"string_value": "test_string"},
    )

    with pytest.raises(ValueError, match="No configuration found in mongodb"):
        config_source.load_config()

@patch("pi_conf.config_settings.MongoClient")
def test_mongo_config_source_multiple_documents(MockClient):
    mock_mongo = MockMongoClient(
        {
            "test_db": MockDatabase(
                {
                    "test_collection": MockCollection(
                        [
                            {"_id": ObjectId(), "doc1": "value1"},
                            {"_id": ObjectId(), "doc2": "value2"}
                        ]
                    )
                }
            )
        }
    )
    MockClient.return_value = mock_mongo

    config_source = MongoConfigSource(
        mongo_uri="mongodb://localhost:27017",
        mongo_database="test_db",
        mongo_collection="test_collection",
        mongo_query={"string_value": "test_string"},
    )
    config = config_source.load_config()

    # Assuming MongoConfigSource returns the first document when multiple are present
    assert config == {"doc1": "value1"}


@patch("pi_conf.config_settings.MongoClient")
def test_mongo_connection_error(MockClient):
    MockClient.side_effect = ServerSelectionTimeoutError("Connection error")

    config_source = MongoConfigSource(
        mongo_uri="mongodb://localhost:27017",
        mongo_database="test_db",
        mongo_collection="test_collection",
        mongo_query={"string_value": "test_string"},
    )

    with pytest.raises(ServerSelectionTimeoutError, match="Connection error"):
        config_source.load_config()


if __name__ == "__main__":
    pytest.main([__file__])
