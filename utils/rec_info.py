import argparse
import sys
import yaml
import ecdsa
import ecdsa.util

from record import Record
from common import default_config_file

parser = argparse.ArgumentParser(prog="rec_info", description="Reads a record from the STDIN and prints various information about it in the YAML format")
parser.add_argument("-c", "--config-file", type=str, default=default_config_file, help="Record configuration YAML file")
parser.add_argument("-r", "--show-region-info", action=argparse.BooleanOptionalAction, default=False, help="Print information about regions")
parser.add_argument("-u", "--show-root-info", action=argparse.BooleanOptionalAction, default=False, help="Print general info about the NFC tag")
parser.add_argument("-d", "--show-data", action=argparse.BooleanOptionalAction, default=False, help="Parse and print region data")
parser.add_argument("-b", "--show-raw-data", action=argparse.BooleanOptionalAction, default=False, help="Print raw region data (HEX)")
parser.add_argument("-m", "--show-meta", action=argparse.BooleanOptionalAction, default=False, help="By default, --show-data hides the meta region. Enabling this option will print it, too.")
parser.add_argument("-a", "--show-all", action=argparse.BooleanOptionalAction, default=False, help="Apply all --show options")
parser.add_argument("-v", "--validate", action=argparse.BooleanOptionalAction, default=False, help="Check that the data are valid")
parser.add_argument("-s", "--verify-ecdsa", type=str, help="Verify ECDSA signature of the sections if present. The argument specifies path to the public key file.")

args = parser.parse_args()

if args.show_all:
    args.show_root_info = True
    args.show_region_info = True
    args.show_data = True
    args.show_meta = True

record = Record(args.config_file, memoryview(bytearray(sys.stdin.buffer.read())))
output = {}

if args.show_region_info or args.show_root_info:
    regions_info = dict()
    payload_used_size = 0

    for name, region in record.regions.items():
        region_info = region.info_dict()
        payload_used_size += region.used_size()

        if region.read().get("is_signed", False):
            signature_size = region.signature_size()
            region_info["signature_size"] = signature_size
            payload_used_size += signature_size

            if args.verify_ecdsa:
                with open(args.verify_ecdsa, "rb") as f:
                    key = ecdsa.VerifyingKey.from_pem(f.read())

                region_info["signature_valid"] = region.verify_signature(lambda signature, data: key.verify(signature, data, sigdecode=ecdsa.util.sigdecode_der))

        regions_info[name] = region_info

    if args.show_region_info:
        output["regions"] = regions_info

    if args.show_root_info:
        overhead = len(record.data) - len(record.payload)
        output["root"] = {
            "message_size": len(record.data),
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

if args.validate:
    for name, region in record.regions.items():
        region.fields.validate(region.read())


def yaml_hex_bytes_representer(dumper: yaml.SafeDumper, data: bytes):
    return dumper.represent_str("0x" + data.hex())


class InfoDumper(yaml.SafeDumper):
    pass


InfoDumper.add_representer(bytes, yaml_hex_bytes_representer)
yaml.dump(output, stream=sys.stdout, Dumper=InfoDumper)
