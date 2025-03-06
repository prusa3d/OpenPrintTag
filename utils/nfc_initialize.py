# Reference implementation of initializing an "empty" Prusa Material NFC tag

import argparse
import ndef
import cbor2
import os
import sys
import types
import yaml

from fields import Fields
from common import default_config_file

# Maximum expected size of the meta section
max_meta_section_size = 8

parser = argparse.ArgumentParser(prog="nfc_initialize", description="Initializes an 'empty' (with no static or aux data) NFC tag to be used as a Prusa Material tag.\n" + "The resulting bytes to be written on the tag are returned to stdout.")
parser.add_argument("-c", "--config-file", type=str, default=default_config_file, help="YAML file with the fields configuration")
parser.add_argument("-s", "--size", type=int, required=True, help="Available space on the NFC tag in bytes")
parser.add_argument("-d", "--aux-region", type=int, help="Allocate auxiliar region of the provided size in bytes.")
parser.add_argument("-b", "--block-size", type=int, default=4, help="Block size of the chip. The regions are aligned with the blocks. 1 = no align")

args = parser.parse_args()

config_dir = os.path.dirname(args.config_file)
with open(args.config_file, "r") as f:
    config = types.SimpleNamespace(**yaml.safe_load(f))

assert config.root == "ndef", "nfc_initialize only supports NFC tags"

ndef_header_size = 3 + len(config.mime_type)
payload_size = args.size - ndef_header_size

# If the NDEF payload size would exceed 255 bytes, its length cannot be stored in a single byte
# and NDEF switches to storing the length into 4 bytes
if payload_size > 255:
    payload_size -= 3

    # If the payload is now smaller, just leave it be
    if payload_size > 255:
        ndef_header_size += 3


payload = bytearray(payload_size)
metadata = dict()
meta_fields = Fields.from_file(os.path.join(config_dir, config.meta_fields))


def write_section(offset: int, data: dict):
    encoded = cbor2.dumps(data)
    enc_len = len(encoded)
    payload[offset : offset + enc_len] = encoded
    return enc_len


def align_region_offset(offset: int, align_up: bool = True):
    """Aligns offset to the NDEF block size"""

    # We're aligning within the whole tag frame, not just within the NFC payload
    misalignment = (ndef_header_size + offset) % args.block_size
    if misalignment == 0:
        return offset

    elif align_up:
        return offset + args.block_size - misalignment

    else:
        return offset - misalignment


# Determine main region offset
# If we are not aligning, we don't need to write the main region offset, it will be directly after the meta region
main_region_offset = 0
if args.block_size > 1:
    # We don't know the meta section actual size, because it is deteremined by how the main_region_offset is encoded - we have to assume maximum
    main_region_offset = align_region_offset(max_meta_section_size)
    metadata["main_region_offset"] = main_region_offset

# Prepare aux region
if args.aux_region is not None:
    aux_region_offset = align_region_offset(payload_size - args.aux_region, align_up=False)
    metadata["aux_region_offset"] = aux_region_offset
    write_section(aux_region_offset, dict())

# Prepare meta section
meta_section_size = write_section(0, meta_fields.encode(metadata))
if main_region_offset == 0:
    main_region_offset = meta_section_size

# Write main region
write_section(main_region_offset, dict())

# Create the NDEF record
ndef_record = ndef.Record(config.mime_type, "", payload)
ndef_data = b"".join(ndef.message_encoder([ndef_record]))

# Check that we have deduced the ndef header size correctly
if len(ndef_data) != ndef_header_size + payload_size:
    sys.exit(f"NDEF record calculated incorrectly: expected size {ndef_header_size + payload_size} ({ndef_header_size} + {payload_size}), but got {len(ndef_data)}")

# Check that the payload is where we expect it to be
assert ndef_data[ndef_header_size:] == payload

# Write the result to the stdout
sys.stdout.buffer.write(ndef_data)
