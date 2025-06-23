# NFC Data Format Specification

## Used standards
- [ISO/IEC 15693-3](https://en.wikipedia.org/wiki/ISO/IEC_15693)
- [NFC Data Exchange Format (NDEF)](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/)
- [Concise Binary Object Representation (CBOR)](https://cbor.io/)

## Overall structure
<table class="packet-structure">
   <tr>
      <td colspan=7>NDEF message</td>
   </tr>
   <tr>
      <td colspan=7>NDEF record</td>
   </tr>
   <tr>
      <td rowspan=3>Record header</td>
      <td colspan=6>Record payload</td>
   </tr>
   <tr>
      <td>Meta region</td>
      <td colspan=3>Main region</td>
      <td colspan=2>Auxiliary region</td>
   </tr>
   <tr>
      <td>Meta section</td>
      <td>Main section</td>
      <td>Main section signature</td>
      <td class="unused">Unused space</td>
      <td>Auxiliary section</td>
      <td class="unused">Unused space</td>
   </tr>
</table>
<style>
   .packet-structure tbody {
      border: 2px solid black;
   }
   .packet-structure td {
      vertical-align: top;
      text-align: center;
      border: 1px solid black;
      border-left: 2px solid black;
      border-right: 2px solid black;
   }
   .packet-structure .unused {
      opacity: 50%;
   }
</style>

- The top layer format of the NFC tag is an NDEF message.
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
         - Presence determined by the `is_signed` field in the main section.
         - If present, the signature **MUST** be encoded as CBOR byte string.
         - We **heavily recommend using ecdsa secp256k1 sha256 DER** signature.
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
1. CBOR maps and arrays should be encoded as indefinite containers
1. `bytes` and `uuid` types are encoded as CBOR byte string

### UUIDs
The specification optionally employs [UUIDs](https://en.wikipedia.org/wiki/Universally_unique_identifier) to uniquely identify various entities referenced in the data.
Because UUIDs are expected to take more space, manufacturers can use their brand-specific IDs instead.

In that case, the UUIDs can be derived from the brand-specific IDs using UUIDv5 with the `SHA1` hash, as specified in [RFC 4122, section 4.3](https://datatracker.ietf.org/doc/html/rfc4122#section-4.3). All UUIDs and numbers are hashed in the binary form, all strings (and bytes) are hashed including the terminating `\0`.

| UID | Derviation formula | Namespace (`N`) |
| --- | --- | --- |
| `brand_uuid` | `N + brand` | `5269dfb7-1559-440a-85be-aba5f3eff2d2` |
| `material_uuid` | `N + brand_uuid + brand_specific_material_id` | `616fc86d-7d99-4953-96c7-46d2836b9be9` |
| `package_uuid` | `N + brand_uuid + brand_specific_package_id` | `6f7d485e-db8d-4979-904e-a231cd6602b2` |
| `instance_uuid` | `N + brand_uid + brand_specific_instance_id` | `ce836047-24e6-49d5-b3e6-3c910c4dfc87` |
| `instance_uuid` | `N + brand_uid + nfc_tag_uid` | `31062f81-b5bd-4f86-a5f8-46367e841508` |


For example:
<!-- Generated using generate_uuid_examples.py -->
* `brand = "Prusament"` → `brand_uid = "2b2ef3a4-8717-574e-976b-251eea76b074"`
* `brand_uuid = "2b2ef3a4-8717-574e-976b-251eea76b074"`, `brand_specific_material_id = 0x01` → `material_uuid = "cda45901-c06b-57a7-a4e4-7d1e7a9c6fa2"`

## Meta section
1. CBOR map, keys are integers.
1. Allows defining of region offsets (within the NDEF payload) and sizes.
   - Main region is always present. If the offset is not specified, the region starts right after the meta section.
   - Auxiliary region is optional (although heavily recommended). Its presence is indicated by the `aux_region_offset` field.

### Field list
{{ fields_table("meta_fields") }}

## Main section
1. CBOR map, keys are integers.
1. Contains material information that does not change during the material lifetime.
   1. This section can possibly be locked by the manufacturer.

### Field list
{{ fields_table("main_fields", "") }}

#### Field list (FFF-specific)
{{ fields_table("main_fields", "fff") }}

#### Field list (SLA-specific)
{{ fields_table("main_fields", "sla") }}

#### `material_class` items
{{ enum_table("material_class_enum") }}

#### `material_type` items
{{ enum_table("material_type_enum") }}

#### `tags` items
{{ enum_table("tags_enum") }}

## Auxiliary section

### Field list
{{ fields_table("aux_fields", "") }}

### Field list (SLA-specific)
{{ fields_table("aux_fields", "sla") }}
