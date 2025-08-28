# Reference implementation of initializing an "empty" Prusa Material NFC tag

import argparse
import ndef
import cbor2_local as cbor2
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
parser.add_argument("-a", "--aux-region", type=int, help="Allocate auxiliar region of the provided size in bytes.")
parser.add_argument("-b", "--block-size", type=int, default=4, help="Block size of the chip. The regions are aligned with the blocks. 1 = no align")
parser.add_argument("-m", "--meta-region", type=int, default=None, help="Meta region allocation size. If not specified, the meta region will only take minimum size required.")
parser.add_argument("-u", "--ndef-uri", type=str, default=None, help="Adds a NDEF record with the specified URI at the beginning of the NDEF message")

args = parser.parse_args()

config_dir = os.path.dirname(args.config_file)
with open(args.config_file, "r") as f:
    config = types.SimpleNamespace(**yaml.safe_load(f))

assert config.root == "ndef", "nfc_initialize only supports NFC tags"

# Set up preceding NDEF regions
records = []
if args.ndef_uri is not None:
    records.append(ndef.UriRecord(args.ndef_uri))

preceding_records_size = len(b"".join(ndef.message_encoder(records)))

ndef_header_size = 3 + len(config.mime_type)
payload_size = args.size - ndef_header_size - preceding_records_size

assert payload_size > max_meta_section_size, "There is not enough space even for the meta region"

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
    misalignment = (preceding_records_size + ndef_header_size + offset) % args.block_size
    if misalignment == 0:
        return offset

    elif align_up:
        return offset + args.block_size - misalignment

    else:
        return offset - misalignment


# Determine main region offset
if (args.block_size > 1) or (args.meta_region is not None):
    # If we don't know the meta section actual size (because it is deteremined by how the main_region_offset is encoded), we have to assume maximum
    main_region_offset = align_region_offset(args.meta_region or max_meta_section_size)
    metadata["main_region_offset"] = main_region_offset
else:
    # If we are not aligning, we don't need to write the main region offset, it will be directly after the meta region
    main_region_offset = None

# Prepare aux region
if args.aux_region is not None:
    assert args.aux_region > 4, "Aux region is too small"

    aux_region_offset = align_region_offset(payload_size - args.aux_region, align_up=False)
    metadata["aux_region_offset"] = aux_region_offset
    write_section(aux_region_offset, dict())

# Prepare meta section
meta_section_size = write_section(0, meta_fields.encode(metadata))
if main_region_offset is None:
    main_region_offset = meta_section_size

if args.aux_region is not None:
    assert aux_region_offset - main_region_offset >= 4, "Main region is too small"
else:
    assert payload_size - main_region_offset >= 8, "Main region is too small"

# Write main region
write_section(main_region_offset, dict())

# Create the NDEF record
records.append(ndef.Record(config.mime_type, "", payload))
ndef_data = b"".join(ndef.message_encoder(records))

# Check that we have deduced the ndef header size correctly
expected_size = preceding_records_size + ndef_header_size + payload_size
if len(ndef_data) != expected_size:
    sys.exit(f"NDEF record calculated incorrectly: expected size {expected_size} ({preceding_records_size} + {ndef_header_size} + {payload_size}), but got {len(ndef_data)}")

# Check that the payload is where we expect it to be
assert ndef_data[preceding_records_size + ndef_header_size :] == payload

# Write the result to the stdout
sys.stdout.buffer.write(ndef_data)
