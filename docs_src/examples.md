# Examples
The OpenPrintTag specification comes with [a set of utilities written in Python]({{repo}}/tree/main/utils) that serve as a baseline/reference implementation.

## Reading a tag
The `rec_info` utility can be used to parse data on the NFC tag into a YAML file that is readable by both humans and computers.
{{ show_example("cat sample_data/sample_tag.bin | >rec_info.py --show-data") }}

## Updating a tag
The `rec_update` utility can be used to update an existing tag with new data.
{{ show_example("cat sample_data/sample_tag.bin | >rec_info.py --show-data --show-root-info") }}
{{ show_file("sample_data/data_to_update.yaml") }}
{{ show_example("cat sample_data/sample_tag.bin | >rec_update.py sample_data/data_to_update.yaml | >rec_info.py --show-data --show-root-info") }}

## Initializing a tag
If you want to create a custom NFC tag from scratch, you first need to use `nfc_initialize` utility to set up the basic tag structure. This is similar to creating a filesystem on a drive.

Some decisions need to be made regarding the structure of the NFC tag:
1. Record size: The capacity of the NFC tag determines the amount of space we can allocate for the data.
2. Auxiliary region for dynamic data: We recommend to allocate a 32B auxiliary region, if the capacity of the NFC tag allows it.

{{ show_example(">nfc_initialize.py --size=300 --aux-region=32 | >rec_info.py --show-all") }}

After initializing the tag, it can be filled with data using `rec_update`.
{{ show_file("sample_data/data_to_fill.yaml") }}
{{ show_example(">nfc_initialize.py --size=300 --aux-region=32 | >rec_update.py sample_data/data_to_fill.yaml | >rec_info.py --show-all") }}

### Prepending an URI

The NFC tag can contain multiple NDEF records. The `init_tag.py` script provides a convenience function for putting an URI NDEF record at the beginning of the tag:

{{ show_example(">nfc_initialize.py --size=300 --aux-region=32 --ndef-uri=https://3dtag.org/c/4ea3c75dc9 | >rec_update.py sample_data/data_to_fill.yaml | >rec_info.py --show-all") }}

### Initializing a smaller chip

Alternative example when we're a bit more tight on the NFC chip size:
{{ show_file("sample_data/compact_data_to_fill.yaml") }}
{{ show_example(">nfc_initialize.py --size=128 --aux-region=16 --block-size=1 | >rec_update.py sample_data/compact_data_to_fill.yaml | >rec_info.py --show-all") }}
