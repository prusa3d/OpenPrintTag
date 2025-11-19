# Reference implementation of initializing an "empty" Prusa Material NFC tag

import simple_parsing
import ndef
import cbor2
import os
import sys
import types
from dataclasses import dataclass
import yaml

from fields import Fields, EncodeConfig
from common import default_config_file

# Maximum expected size of the meta section
max_meta_section_size = 8


@dataclass
class Args:
    """Following command line arguments are accepted (you can also use the file as a module)"""

    # Available space on the NFC tag in bytes
    size: int = simple_parsing.field(alias=["-s"])

    # YAML file with the fields configuration
    config_file: str = simple_parsing.field(default=default_config_file, alias=["-c", "--config-file"])

    # Block size of the chip. The aux region is aligned with the blocks. 1 = no align
    block_size: int = simple_parsing.field(default=4, alias=["-b", "--block-size"])

    # Allocate an auxiliary region of the provided size in bytes.
    aux_region: int = simple_parsing.field(default=None, alias=["-a", "--aux-region"])

    # Meta region allocation size. If not specified, the meta region will only take minimum size required.
    meta_region: int = simple_parsing.field(default=None, alias=["-m", "--meta-region"])

    # If specified, Adds a NDEF record with the specified URI at the beginning of the NDEF message
    ndef_uri: str = simple_parsing.field(default=None, alias=["-u", "--ndef-uri"])


def nfc_initialize(args: Args):
    config_dir = os.path.dirname(args.config_file)
    with open(args.config_file, "r", encoding="utf-8") as f:
        config = types.SimpleNamespace(**yaml.safe_load(f))

    assert config.root == "nfcv", "nfc_initialize only supports NFC-V tags"

    # Set up TLV and CC
    assert (args.size % 8) == 0, f"Tag size {args.size} must be divisible by 8 (to be encodable in the CC)"
    assert args.size / 8 <= 255, "Tag too big to be representable in the CC"
    capability_container = bytes(
        [
            0xE1,  # Magic number
            0x40  # Version 1.0 (upper 4 bits)
            | 0x0,  # Read/write access without restrictions (lower 4 bits)
            args.size // 8,
            #
            # Capabilities - TAG SPECIFIC!
            0x01,  # MBREAD - supports "Read Multiple Blocks" command - SLIX2 DOES
            # | 0x02 # IPREAD - supports "Inventory Page Read" command - SLIX2 does NOT
        ]
    )
    capability_container_size = len(capability_container)

    tlv_terminator = bytes([0xFE])

    ndef_tlv_header_size = 2

    # Our NDEF record will be adjusted so that the message fills the whole available space
    ndef_message_length = args.size - capability_container_size - len(tlv_terminator) - ndef_tlv_header_size

    if ndef_message_length > 0xFE:
        # We need two more bytes to encode longer TLV lenghts
        ndef_tlv_header_size += 2
        ndef_message_length -= 2

    # Do not merge with the previous if - the available space decrease might get us under this line
    if ndef_message_length <= 0xFE:
        ndef_tlv_header = bytes(
            [
                0x03,  # NDEF Message tag
                ndef_message_length,
            ]
        )
    else:
        ndef_tlv_header = bytes(
            [
                0x03,  # NDEF Message tag
                0xFF,
                ndef_message_length // 256,
                ndef_message_length % 256,
            ]
        )

    assert len(ndef_tlv_header) == ndef_tlv_header_size

    # Set up preceding NDEF regions
    records = []
    if args.ndef_uri is not None:
        records.append(ndef.UriRecord(args.ndef_uri))

    preceding_records_size = len(b"".join(ndef.message_encoder(records)))

    ndef_header_size = 3 + len(config.mime_type)
    ndef_payload_start = capability_container_size + ndef_tlv_header_size + preceding_records_size + ndef_header_size
    payload_size = ndef_message_length - ndef_header_size - preceding_records_size

    assert payload_size > max_meta_section_size, "There is not enough space even for the meta region"

    # If the NDEF payload size would exceed 255 bytes, its length cannot be stored in a single byte
    # and NDEF switches to storing the length into 4 bytes
    if payload_size > 255:
        ndef_header_size += 3
        ndef_payload_start += 3
        payload_size -= 3

        # If we now got back under 255, the ndef payload length will be shorter again and we wouldn't fill the NDEF message fully to the TLV-dictated size
        # This could be resolved by enforcing the longer NDEF header in this case anyway, but the NDEF library does not support it - we'd need to construct the NDEFs by ourselves
        assert payload_size > 255, "Unable to fill the NDEF message correctly"

    payload = bytearray(payload_size)
    metadata = dict()
    meta_fields = Fields.from_file(os.path.join(config_dir, config.meta_fields))

    def write_section(offset: int, data: bytes):
        enc_len = len(data)
        payload[offset : offset + enc_len] = data
        return enc_len

    def align_region_offset(offset: int, align_up: bool = True):
        """Aligns offset to the NDEF block size"""

        # We're aligning within the whole tag frame, not just within the NFC payload
        misalignment = (ndef_payload_start + offset) % args.block_size
        if misalignment == 0:
            return offset

        elif align_up:
            return offset + args.block_size - misalignment

        else:
            return offset - misalignment

    # Determine main region offset
    if args.meta_region is not None:
        # If we don't know the meta section actual size (because it is deteremined by how the main_region_offset is encoded), we have to assume maximum
        main_region_offset = args.meta_region
        metadata["main_region_offset"] = main_region_offset
    else:
        # If we are not aligning, we don't need to write the main region offset, it will be directly after the meta region
        main_region_offset = None

    # Prepare aux region
    if args.aux_region is not None:
        assert args.aux_region > 4, "Aux region is too small"

        aux_region_offset = align_region_offset(payload_size - args.aux_region, align_up=False)
        metadata["aux_region_offset"] = aux_region_offset
        write_section(aux_region_offset, cbor2.dumps({}))

    # Prepare meta section
    # Indefinite containers take one extra byte, don't do that for the meta region - that one won't likely ever be updated
    meta_section_size = write_section(0, meta_fields.encode(metadata, EncodeConfig(indefinite_containers=False)))
    if main_region_offset is None:
        main_region_offset = meta_section_size

    if args.aux_region is not None:
        assert aux_region_offset - main_region_offset >= 4, "Main region is too small"
    else:
        assert payload_size - main_region_offset >= 8, "Main region is too small"

    # Write main region
    write_section(main_region_offset, cbor2.dumps({}))

    # Create the NDEF record
    records.append(ndef.Record(config.mime_type, "", payload))
    ndef_data = b"".join(ndef.message_encoder(records))

    assert len(ndef_data) == ndef_message_length

    # Check that we have deduced the ndef header size correctly
    expected_size = preceding_records_size + ndef_header_size + payload_size
    if len(ndef_data) != expected_size:
        sys.exit(f"NDEF record calculated incorrectly: expected size {expected_size} ({preceding_records_size} + {ndef_header_size} + {payload_size}), but got {len(ndef_data)}")

    full_data = bytes()
    full_data += capability_container
    full_data += ndef_tlv_header
    full_data += ndef_data
    full_data += tlv_terminator

    # The full data can be slightly smaller because we might have decreased ndef_tlv_available_space by 2 to fit the bigger TLV header and then ended up not needing the bigger TLV header
    assert args.size - 1 <= len(full_data) <= args.size

    # Check that the payload is where we expect it to be
    assert full_data[ndef_payload_start : ndef_payload_start + payload_size] == payload

    return full_data


if __name__ == "__main__":
    parser = simple_parsing.ArgumentParser(
        prog="nfc_initialize",
        description="Initializes an 'empty' (with no static or aux data) NFC tag to be used as a Prusa Material tag.\nThe resulting bytes to be written on the tag are returned to stdout.",
    )
    parser.add_arguments(Args, dest="args")
    sys.stdout.buffer.write(nfc_initialize(parser.parse_args().args))
