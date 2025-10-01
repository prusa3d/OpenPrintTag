import argparse
import sys
import yaml

from record import Record
from common import default_config_file

parser = argparse.ArgumentParser(prog="rec_info", description="Reads a record from the STDIN and prints various information about it in the YAML format")
parser.add_argument("-c", "--config-file", type=str, default=default_config_file, help="Record configuration YAML file")
parser.add_argument("-r", "--show-region-info", action=argparse.BooleanOptionalAction, default=False, help="Print information about regions")
parser.add_argument("-u", "--show-root-info", action=argparse.BooleanOptionalAction, default=False, help="Print general info about the NFC tag")
parser.add_argument("-d", "--show-data", action=argparse.BooleanOptionalAction, default=False, help="Parse and print region data")
parser.add_argument("-b", "--show-raw-data", action=argparse.BooleanOptionalAction, default=False, help="Print raw region data (HEX)")
parser.add_argument("-m", "--show-meta", action=argparse.BooleanOptionalAction, default=False, help="By default, --show-data hides the meta region. Enabling this option will print it, too.")
parser.add_argument("-i", "--show-uri", action=argparse.BooleanOptionalAction, default=False, help="If a URI NDEF record is present, report it as well.")
parser.add_argument("-a", "--show-all", action=argparse.BooleanOptionalAction, default=False, help="Apply all --show options")
parser.add_argument("-v", "--validate", action=argparse.BooleanOptionalAction, default=False, help="Check that the data are valid")
parser.add_argument("-f", "--extra-required-fields", type=str, default=None, help="Check that all fields from the specified YAML file are present in the record")

args = parser.parse_args()

if args.show_all:
    args.show_root_info = True
    args.show_region_info = True
    args.show_data = True
    args.show_meta = True
    args.show_uri = True

record = Record(args.config_file, memoryview(bytearray(sys.stdin.buffer.read())))
output = {}

if args.show_region_info or args.show_root_info:
    regions_info = dict()
    payload_used_size = 0

    for name, region in record.regions.items():
        region_info = region.info_dict()
        payload_used_size += region.used_size()
        regions_info[name] = region_info

    if args.show_region_info:
        output["regions"] = regions_info

    if args.show_root_info:
        overhead = len(record.data) - len(record.payload)
        output["root"] = {
            "data_size": len(record.data),
            "payload_size": len(record.payload),
            "overhead": overhead,
            "payload_used_size": payload_used_size,
            "total_used_size": payload_used_size + overhead,
        }

if args.show_data:
    data = {}

    for name, region in record.regions.items():
        if args.show_meta or name != "meta":
            data[name] = region.read()

    output["data"] = data

if args.show_raw_data:
    data = {}

    for name, region in record.regions.items():
        if args.show_meta or name != "meta":
            data[name] = region.memory.hex()

    output["raw_data"] = data

if args.show_uri:
    output["uri"] = record.uri

if args.validate:
    for name, region in record.regions.items():
        region.fields.validate(region.read())

if args.extra_required_fields:
    with open(args.extra_required_fields, "r") as f:
        req_fields = yaml.safe_load(f)

    for region_name, region_req_fields in req_fields.items():
        region = record.regions.get(region_name)
        assert region, f"Missing region {region_name}"

        region_data = region.read()

        for req_field_name in region_req_fields:
            assert req_field_name in region_data, f"Missing field '{req_field_name}' in region '{region_name}'"


def yaml_hex_bytes_representer(dumper: yaml.SafeDumper, data: bytes):
    return dumper.represent_str("0x" + data.hex())


class InfoDumper(yaml.SafeDumper):
    pass


InfoDumper.add_representer(bytes, yaml_hex_bytes_representer)
yaml.dump(output, stream=sys.stdout, Dumper=InfoDumper, sort_keys=False)
