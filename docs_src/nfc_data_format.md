# NFC Data Format Specification
## Used standards
- [NFC Data Exchange Format (NDEF)](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/)
- [Concise Binary Object Representation (CBOR)](https://cbor.io/)

## Overall structure

- The top layer format of the NFC chip is an NDEF message.
- The message has an **NDEF record** of MIME type **application/vnd.prusa3d.mat.nfc**.
   - The material record should be the first one within the message. Adding further records is allowed.
   - The payload of the record consists of:
      1. **Meta section** (CBOR map)
         - Always at the beginning of the payload.
         - Contains information about other regions:
            - Region is a part of the payload allocated for the respective section.
            - A section does not have to fill the whole region.
      1. **Main section** (CBOR map)
         - Positioned at the beginning of the main region.
         - Intended for static information, not intended to be updated by printers.
            - The only situation where this region needs to be updated would be when the container is being repurposed.
      1. **Main section signature** (optional, CBOR byte string)
         - Immediately follows the main section, still part of the main region.
         - Presence determined by the `signed` field in the main section.
         - If present, the signature **MUST** be encoded as CBOR byte string.
         - We **heavily recommend using ecdsa secp256k1** signature encoded in the DER format (and then in CBOR).
            - Having the same signature type everywhere enables optimizations for firmware developers.
      1. **Auxiliary section** (optional, CBOR map)
         - Positioned at the beginning of the auxiliary region.
         - Intended for dynamic information, intended to be updated by the printers.

## Specification common to all sections
1. Data of all sections in the specification are represented as a CBOR map.
   - Keys of the map are integers. Semantics of the keys are specific to each section.
   - The reader must be able to skip all unknown keys, of any data type.
1. `enum` fields are encoded as an integer, according to the enum field mapping
1. `enum_array` fields are encoded as CBOR arrays of integers, according to the field mapping
1. `timestamp` fields are encoded as UNIX timestamp integers
1. `❗` means required, `❕` means recommended

## Meta section
1. CBOR map, keys are integers.
1. Allows defining of region offsets (within the NDEF payload) and sizes.
   - Main region is always present. If the offset is not specified, the region starts right after the meta section.
   - Auxiliary region is optional (although heavily recommended). Its presence is indicated by the `aux_region_offset` field.

### Fields list
{{ fields_table("meta_fields") }}

## Main section
1. CBOR map, keys are integers.
1. Contains material information that does not change during the material lifetime.
   1. This section can possibly be locked by the manufacturer.

### Fields list
{{ fields_table("main_fields") }}

#### `material_class` items
{{ enum_table("material_class_enum") }}

#### `material_type` items
{{ enum_table("material_type_enum") }}

#### `tags` items
{{ enum_table("tags_enum") }}

## Auxiliary section

### Fields list
{{ fields_table("aux_fields") }}

## Notes & recommendations
   1. **The NDEF record shall not be split into multiple NDEF record chunks.**
      - Splitting the record would break the "virtual space" of the payload and would complicate implementation.
   1. We recommend to **expand the payload of the NDEF record so that the whole available memory of the NFC tag is used.**
      - The idea is that the factory can fully lock the blocks containing the NDEF  headers and would only the memory pool open. (Possibly write protecting  part of it as well).
      - Part of the memory pool is auxiliary section, which we want to be able to write to without having to edit other structures/shuffle things around.
   1. The meta section allows the manufacturers to configure the payload structure so that it fits their purposes and the used NFC tag specifics:
      1. The auxiliary region can be adjusted or even omitted, based on the NFC tag available memory.
         - It is not specified that the auxiliary region must be after the main region. Auxiliary region can possibly be located **before** the main region, if the meta section says so. We however recommend **putting the main region before the auxiliary region**, so that it can be protected together with the NDEF header.
      1. NFC tags can allow block-level locking (`LOCK BLOCK`, making the data completely read-only).
         - We recommend **aligning the regions with the NFC tag blocks** (typically 4 B).
         - The NDEF header and the meta section can possibly be fully locked after the first write.
         - **We do not recommend locking the main region** this way. We aim to keep the NFC tags reusable.
      1. NFC tags can also support page-level password protection (`PROTECT PAGE`).
         - **Protecting the auxiliary region is not supported**. The auxiliary region needs to be writable without any protection at all times.
         - In case of protecting the main region, we recommend:
            1. Use a unique password for each package instance.
            1. Put the password on a label somewhere on the container.
            1. The label should not be accessible without unpacking the container.
            1. The label should be attached on the container itself.
            1. The password should be readable for both humans and machines (typically text + QR code).