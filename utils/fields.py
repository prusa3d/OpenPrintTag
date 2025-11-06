import yaml
import os
import numpy
import uuid
import sys
import typing
import cbor2
import io
import dataclasses


@dataclasses.dataclass
class EncodeConfig:
    # Encode CBOR canonically (order map entries)
    canonical: bool = True

    # Encode using indefinite containers
    indefinite_containers: bool = True


# Without this bit of magic, the cbor2 Python library encodes some floats (for example 0.3) as 8 B doubles - we don't want that, it wastes space
class CompactFloat:
    decimal_precision = 3
    required_precision = pow(10, -decimal_precision)

    value: float

    def __init__(self, num: float):
        num = float(num)

        if num.is_integer():
            self.value = int(num)

        elif abs(num - numpy.float16(num)) < CompactFloat.required_precision:
            self.value = float(numpy.float16(num))

        elif abs(num - numpy.float32(num)) < CompactFloat.required_precision:
            self.value = float(numpy.float32(num))

        else:
            self.value = num


class Field:
    key: int
    name: str
    required: bool

    def __init__(self, config, config_dir):
        self.type_name = config["type"]
        self.key = int(config["key"])
        self.name = str(config["name"])
        self.required = config.get("required", False)


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
        return int(num) if num.is_integer() else round(num, CompactFloat.decimal_precision)

    def encode(self, data):
        return CompactFloat(data)


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


class EnumFieldBase(Field):
    items_by_key: dict[str, int]
    items_by_name: dict[int, str]
    items_yaml: list[dict]

    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)

        self.items_by_key = dict()
        self.items_by_name = dict()

        self.items_yaml = yaml.safe_load(open(os.path.join(config_dir, config["items_file"]), "r"))
        for item in self.items_yaml:
            if item.get("deprecated", False):
                continue

            key = int(item[config.get("index_field", "key")])
            name = str(item[config.get("name_field", "name")])

            assert key not in self.items_by_key, f"Key '{key}' already exists"
            assert name not in self.items_by_name, f"Item '{name}' already exists"

            self.items_by_key[key] = name
            self.items_by_name[name] = key


class EnumField(EnumFieldBase):
    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)

    def decode(self, data):
        return self.items_by_key[data]

    def encode(self, data):
        return self.items_by_name[data]


class EnumArrayField(EnumFieldBase):
    def __init__(self, config, config_dir):
        super().__init__(config, config_dir)

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
        assert "max_length" in config, f"max_length not specified for '{config['name']}'"
        self.max_len = config["max_length"]

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

    def from_file(file: str):
        r = Fields()
        r.init_from_yaml(yaml.safe_load(open(file, "r")), os.path.dirname(file))

        return r

    # Decodes the fields and values from the CBOR binary data
    # If out_unknown_fields is provided, unknown fields are written into it instead of asserting
    def decode(self, binary_data: typing.IO[bytes], out_unknown_fields: dict[any, any] = None):
        data = cbor2.load(binary_data)
        result = dict()
        for key, value in data.items():
            field = self.fields_by_key.get(key)

            if field is None and out_unknown_fields is not None:
                out_unknown_fields[key] = value
                continue

            assert field, f"Unknown CBOR key '{key}'"

            try:
                result[field.name] = field.decode(value)
            except Exception as e:
                e.add_note(f"Field {key} {field.name}")
                raise

        return result

    # Encodes keys and field values to a cbor-ready dictionary
    def encode(self, data: dict[str, any], config: EncodeConfig = EncodeConfig()) -> bytes:
        return self.update(update_fields=data, config=config)

    def update(self, original_data: typing.IO[bytes] = None, update_fields: dict[str, any] = {}, remove_fields: list[str] = [], config: EncodeConfig = EncodeConfig()) -> bytes:
        if original_data:
            result = cbor2.load(original_data)
        else:
            result = dict()

        for field_name in remove_fields:
            field = self.fields_by_name.get(field_name)
            assert field, f"Unknown field '{field_name}'"

            del result[field.key]

        for field_name, value in update_fields.items():
            field = self.fields_by_name.get(field_name)
            assert field, f"Unknown field '{field_name}'"

            try:
                result[field.key] = field.encode(value)
            except Exception as e:
                e.add_note(f"Field {field.key} {field.name}")
                raise

        # Enforce use of CompactFloat, the "default" float encoding is not optimal when canonical == False
        for field_name, value in result.copy().items():
            if isinstance(value, float):
                result[field_name] = CompactFloat(value)

        def default_enc(enc: cbor2.CBOREncoder, data: typing.Any):
            if isinstance(data, CompactFloat):
                # Always encode floats canonically
                # Noncanonically, floats would always be encoded in 8 B, which is a lot of wasted space
                cbor2.CBOREncoder(enc.fp, canonical=True).encode(data.value)
            else:
                raise RuntimeError(f"Unsupported type {type(data)} to encode")

        data_io = io.BytesIO()
        encoder = cbor2.CBOREncoder(
            data_io,
            canonical=config.canonical,
            indefinite_containers=config.indefinite_containers,
            default=default_enc,
        )

        encoder.encode(result)
        return data_io.getvalue()

    def validate(self, decoded_data):
        for field_name, field in self.fields_by_name.items():
            if field_name in decoded_data:
                continue

            match field.required:
                case False:
                    pass

                case True:
                    assert False, f"Missing required field '{field.name}'"

                case "recommended":
                    print(f"Missing recommended field '{field.name}'", file=sys.stderr)

                case _:
                    assert False, f"Invalid field '{field.name}' 'required' value '{field.required}'"
