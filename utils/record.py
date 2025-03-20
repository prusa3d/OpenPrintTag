import os
import ndef
import yaml
import cbor2
import io
import types

from fields import Fields


class Region:
    memory: memoryview
    offset: int
    fields: Fields

    def __init__(self, offset: int, memory: memoryview, fields: Fields):
        assert type(memory) is memoryview

        self.offset = offset
        self.memory = memory
        self.fields = fields

        assert len(self.memory) > 0

    def info_dict(self):
        return {
            "offset": self.offset,
            "size": len(self.memory),
            "used_size": self.used_size(),
        }

    def used_size(self):
        data_io = io.BytesIO(self.memory)
        cbor2.load(data_io)
        return data_io.tell()

    def read(self):
        return self.fields.decode(cbor2.loads(self.memory))

    def write(self, data):
        self.memory[:] = bytearray(len(self.memory))
        encoded = cbor2.dumps(self.fields.encode(data), canonical=True)
        assert len(encoded) <= len(self.memory), f"Data of size {len(encoded)} does not fit into region of size {len(self.memory)}"
        self.memory[0 : len(encoded)] = encoded

    def sign(self, sign_f):
        used_size = self.used_size()
        signature = cbor2.dumps(sign_f(self.memory[0:used_size]), canonical=True)
        signature_len = len(signature)
        memory_len = len(self.memory)

        assert used_size + signature_len <= memory_len, f"Signature doesn't fit in the region ({used_size} + {signature_len} > {memory_len})"
        self.memory[used_size : used_size + signature_len] = signature

    def verify_signature(self, verify_f):
        used_size = self.used_size()
        signature = cbor2.loads(self.memory[used_size:])
        return verify_f(signature, self.memory[:used_size])

    def signature_size(self):
        data_io = io.BytesIO(self.memory[self.used_size() :])
        cbor2.load(data_io)
        return data_io.tell()


class Record:
    data: memoryview
    payload: memoryview
    config: types.SimpleNamespace
    config_dir: str

    meta_region: Region = None
    main_region: Region = None
    aux_region: Region = None

    regions: dict[str, Region] = None

    def __init__(self, config_file: str, data: memoryview):
        assert type(data) is memoryview

        self.data = data

        self.config_dir = os.path.dirname(config_file)
        with open(config_file, "r") as f:
            self.config = types.SimpleNamespace(**yaml.safe_load(f))

        # Decode the root and find payload
        match self.config.root:
            case "none":
                self.payload = data

            case "ndef":
                data_io = io.BytesIO(data)
                for record in ndef.message_decoder(data_io):
                    if record.type == self.config.mime_type:
                        # We have to create a sub memoryview so that when we update the region, the outer data updates as well
                        end = data_io.tell()
                        self.payload = data[end - len(record.data) : end]
                        assert self.payload == record.data
                        break

                else:
                    raise Exception(f"Did not find a record of type '{self.config.mime_type}'")

            case _:
                raise Exception(f"Unknown root type '{self.config.root}'")

        assert type(self.payload) is memoryview
        self._setup_regions()

    def _setup_regions(self):
        if "meta_fields" not in self.config.__dict__:
            # If meta region is not present, we only have the main region which spans the entire payload
            self.main_region = Region(0, self.payload, Fields.from_file(os.path.join(self.config_dir, self.config.main_fields)))
            self.regions = {"main", self.main_region}
            return

        meta_io = io.BytesIO(self.payload)
        cbor2.load(meta_io)
        self.meta_region = Region(0, self.payload[0 : meta_io.tell()], Fields.from_file(os.path.join(self.config_dir, self.config.meta_fields)))
        metadata = self.meta_region.read()

        main_region_offset = metadata.get("main_region_offset", len(self.meta_region.memory))
        main_region_size = metadata.get("main_region_size")

        aux_region_offset = metadata.get("aux_region_offset")
        aux_region_size = metadata.get("aux_region_size")
        has_aux_region = aux_region_offset is not None
        assert (not has_aux_region) or (aux_region_size is None), "aux_region_size present without aux_region_offset"

        region_stops = list(filter(lambda x: x is not None, [main_region_offset, aux_region_offset, len(self.payload)]))
        region_stops.sort()

        def create_region(offset, size, fields):
            if size is None:
                size = list(filter(lambda a: a > offset, region_stops))[0] - offset

            return Region(offset, self.payload[offset : offset + size], Fields.from_file(os.path.join(self.config_dir, fields)))

        self.main_region = create_region(main_region_offset, main_region_size, self.config.main_fields)
        self.regions = {"meta": self.meta_region, "main": self.main_region}

        if has_aux_region:
            self.aux_region = create_region(aux_region_offset, aux_region_size, self.config.aux_fields)
            self.regions["aux"] = self.aux_region
