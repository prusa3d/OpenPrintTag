import yaml
import os
import numpy
import uuid


class Field:
    key: int
    name: str
    required: bool

    def __init__(self, config, config_dir):
        self.type_name = config["type"]
        self.key = int(config["key"])
        self.name = str(config["name"])
        self.required = bool(config.get("required", False))


class BoolField(Field):
    def decode(self, data):
        return bool(data)

    def encode(self, data):
        return bool(data)


class IntField(Field):
    def decode(self, data):
        return int(data)

    def encode(self, data):
        return int(data)


class NumberField(Field):
    def decode(self, data):
        num = float(data)
        return int(num) if num.is_integer() else round(num, 3)

    def encode(self, data):
        # If the number is whole, encode it as int - CBOR does that way more efficiently
        # If it is decimal, store it as half-precision float, which should be plenty for all use cases here
        num = float(data)
        if num.is_integer():
            return int(num)

        encoded = float(numpy.float16(num))
        if abs(num - encoded) < 1e-3:
            return encoded

        encoded = float(numpy.float32(num))
        if abs(num - encoded) < 1e-3:
            return encoded

        assert False, f"Cannot reasonably encode decimal"


class StringField(Field):
    max_len: int

    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)
        self.max_len = config["max_length"]

    def decode(self, data):
        return str(data)

    def encode(self, data):
        result = str(data)
        assert len(result) <= self.max_len
        return result


class EnumField(Field):
    items_by_key: dict[str, int]
    items_by_name: dict[int, str]

    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)

        self.items_by_key = dict()
        self.items_by_name = dict()

        items = yaml.safe_load(open(os.path.join(config_dir, config["items_file"]), "r"))
        for item in items:
            key = int(item["key"])
            name = str(item["name"])

            assert key not in self.items_by_key, f"Key '{key}' already exists"
            assert name not in self.items_by_name, f"Item '{name}' already exists"

            self.items_by_key[key] = name
            self.items_by_name[name] = key

    def decode(self, data):
        return self.items_by_key[data]

    def encode(self, data):
        return self.items_by_name[data]


class EnumArrayField(Field):
    items_by_key: dict[str, int]
    items_by_name: dict[int, str]

    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)

        self.items_by_key = dict()
        self.items_by_name = dict()

        items = yaml.safe_load(open(os.path.join(config_dir, config["items_file"]), "r"))
        for item in items:
            key = int(item["key"])
            name = str(item["name"])

            assert key not in self.items_by_key, f"Key '{key}' already exists"
            assert name not in self.items_by_name, f"Item '{name}' already exists"

            self.items_by_key[key] = name
            self.items_by_name[name] = key

    def decode(self, data):
        assert type(data) is list

        result = []
        for item in data:
            result.append(self.items_by_key[item])

        return result

    def encode(self, data):
        assert type(data) is list

        result = []
        for item in data:
            result.append(self.items_by_name[item])

        return result


class BytesField(Field):
    max_len: int | None

    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)
        self.max_len = config.get("max_length")

    def decode(self, data):
        assert isinstance(data, bytes)
        return {"hex": data.hex()}

    def encode(self, data):
        if isinstance(data, bytes):
            result = data

        elif isinstance(data, str):
            result = data.encode("utf-8")

        elif isinstance(data, int):
            return data.to_bytes(64, "little").rstrip(b"\x00")

        elif isinstance(data, list):
            result = bytearray(data)

        elif isinstance(data, dict):
            result = bytearray.fromhex(data["hex"])

        else:
            assert False, f"Cannot encode type {type(data)} to bytes"

        assert self.max_len is None or len(result) <= self.max_len
        return result


class UUIDField(Field):
    def decode(self, data):
        return str(uuid.UUID(bytes=data))

    def encode(self, data):
        return uuid.UUID(data).bytes


field_types = {
    "bool": BoolField,
    "int": IntField,
    "number": NumberField,
    "string": StringField,
    "enum": EnumField,
    "enum_array": EnumArrayField,
    "timestamp": IntField,
    "bytes": BytesField,
    "uuid": UUIDField,
}


class Fields:
    fields_by_key: dict[int, Field]
    fields_by_name: dict[str, Field]
    required_fields: list[Field]

    def __init__(self):
        self.fields_by_key = dict()
        self.fields_by_name = dict()
        self.required_fields = list()

    def init_from_yaml(self, yaml, config_dir):
        for row in yaml:
            if row.get("deprecated", False):
                continue

            field_type_str = row.get("type")
            assert field_type_str, f"Field type not specified '{row}'"

            field_type = field_types.get(field_type_str)
            assert field_type, f"Unknown field type '{field_type_str}'"
            field = field_type(row, config_dir)

            assert field.key not in self.fields_by_key, f"Field {field.name} duplicit key {field.key}"
            assert field.name not in self.fields_by_name

            self.fields_by_key[field.key] = field
            self.fields_by_name[field.name] = field

            if field.required:
                self.required_fields.append(field)

    def from_file(file: str):
        r = Fields()
        r.init_from_yaml(yaml.safe_load(open(file, "r")), os.path.dirname(file))

        return r

    # Decodes the fields and values from the cbor-read dictionary
    def decode(self, data):
        result = dict()
        for key, value in data.items():
            field = self.fields_by_key.get(key)
            assert field, f"Unknown CBOR key '{key}'"

            try:
                result[field.name] = field.decode(value)
            except Exception as e:
                e.add_note(f"Field {key}")
                raise

        return result

    # Encodes keys and field values to a cbor-ready dictionary
    def encode(self, data):
        result = dict()
        for key, value in data.items():
            field = self.fields_by_name.get(key)
            assert field, f"Unknown field '{key}'"

            try:
                result[field.key] = field.encode(value)
            except Exception as e:
                e.add_note(f"Field {key}")
                raise

        return result

    def validate(self, decoded_data):
        for field in self.required_fields:
            assert field.name in decoded_data, f"Missing required field '{field.name}'"
