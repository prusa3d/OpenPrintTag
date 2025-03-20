import sys
import argparse
import yaml
import ecdsa
import ecdsa.util

from record import Record
from common import default_config_file

parser = argparse.ArgumentParser(prog="rec_update", description="Reads a record from STDIN and updates its fields according to the provided YAML file. Updated record is then printed to stdout.")
parser.add_argument("update_data", help="YAML file with instructions how to update the file")
parser.add_argument("-c", "--config-file", type=str, default=default_config_file, help="Record configuration YAML file")
parser.add_argument("-s", "--sign-ecdsa", type=str, help="If specified, signs the main region using the provided PEM key")
parser.add_argument("--clear", action=argparse.BooleanOptionalAction, default=False, help="If set, the regions mentioned in the YAML file will be cleared rather than updated")
parser.add_argument("--indefinite-containers", action=argparse.BooleanOptionalAction, default=True, help="Encode CBOR containers as indefinite (using stop code instead of specifying length)")

args = parser.parse_args()

record = Record(args.config_file, memoryview(bytearray(sys.stdin.buffer.read())))
record.encode_indefinite_containers = args.indefinite_containers

update_data = yaml.safe_load(open(args.update_data, "r"))
for region_name, update_data in update_data.get("data", dict()).items():
    region = record.regions[region_name]

    if args.clear:
        region_data = dict()
    else:
        region_data = region.read()

    for key, value in update_data.items():
        region_data[key] = value

    region.write(region_data)

if args.sign_ecdsa is not None:
    with open(args.sign_ecdsa, "rb") as f:
        key = ecdsa.SigningKey.from_pem(f.read())

    record.main_region.sign(lambda data: key.sign(data, sigencode=ecdsa.util.sigencode_der))

sys.stdout.buffer.write(record.data)
