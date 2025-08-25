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
      1. **Auxiliary section** (optional, CBOR map)
         - Positioned at the beginning of the auxiliary region.
         - Intended for dynamic information, intended to be updated by the printers.

## Specification common to all sections
1. Data of all sections in the specification are represented as a CBOR map.
   - Keys of the map are integers. Semantics of the keys are specific to each section.
   - All data sections must be at most 512 bytes long.
   - All fields MUST follow this specification. Using custom or vendor-specific keys is not permitted (with the exception described in the Aux Region section).
   - New keys can be added to the specification at any time, so implementations MUST be able to skip all unknown keys, of any type.
   - Keys can be deprecated at any time. Deprecated keys will never be reused.
1. `enum` fields are encoded as an integer, according to the enum field mapping
1. `enum_array` fields are encoded as CBOR arrays of integers, according to the field mapping
1. `timestamp` fields are encoded as UNIX timestamp integers
1. CBOR maps and arrays should be encoded as indefinite containers
1. `bytes` and `uuid` types are encoded as CBOR byte string

### UUIDs
Each entity referenced in the data can be identified by a [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier). The UUID MAY be explicitly specified through a `XX_uuid`, however that might not be desirable due to space constraints. As an alternative, the following algorithm defines a way to derive UUIDs from other fields.

UUIDs are be derived from the brand-specific IDs using UUIDv5 with the `SHA1` hash, as specified in [RFC 4122, section 4.3](https://datatracker.ietf.org/doc/html/rfc4122#section-4.3), according to the following table. UUIDs are hashed in the binary form, strings are encoded as UTF-8. `+` represents binary concatenation.

| UID | Derviation formula | Namespace (`N`) |
| --- | --- | --- |
| `brand_uuid` | `N + brand_name` | `5269dfb7-1559-440a-85be-aba5f3eff2d2` |
| `material_uuid` | `N + brand_uuid + material_name` | `616fc86d-7d99-4953-96c7-46d2836b9be9` |
| `package_uuid` | `N + brand_uuid + gtin` | `6f7d485e-db8d-4979-904e-a231cd6602b2` |
| `instance_uuid` | `N + brand_uid + nfc_tag_uid` | `31062f81-b5bd-4f86-a5f8-46367e841508` |


For example:
{% python %}
def generate_uuid(namespace, *args):
   import uuid
   return uuid.uuid5(uuid.UUID(namespace), b"".join(args))

brand_namespace = "5269dfb7-1559-440a-85be-aba5f3eff2d2"
brand_name = "Prusament"
brand_uuid = generate_uuid(brand_namespace, brand_name.encode("utf-8"))
print(f"brand_uuid = {brand_uuid}")

material_namespace = "616fc86d-7d99-4953-96c7-46d2836b9be9"
gtin = (1234).to_bytes(4, "little")
material_uuid = generate_uuid(material_namespace, brand_uuid.bytes, gtin)
print(f"material_uuid = {material_uuid}")
{% endpython %}

UUIDs MAY thus be omitted from the in most cases. In the case that a brand changes its name, it SHOULD add `brand_uuid` field with the original UUID whenever the new brand name is used:
1. `brand_name = Prusament` (present in the data), `brand_uuid = ae5ff34e-298e-50c9-8f77-92a97fb30b0` (not present, can be automatically computed)
1. Brand gets renamed to `Pepament`
1. `brand_name = Pepament` (present in the data), `brand_uuid = ae5ff34e-298e-50c9-8f77-92a97fb30b0` (present in the data)

NFC tags have a hardcoded UID (referenced as `nfc_tag_uid` in the table above), which can be used for deriving the `instance_uuid`. This is only admissible when the NFC tag is being filled with data for the first time; when reusing the NFC tag for a different material, a new `instance_uuid` MUST be generated and present in the tag to indicate that the package now holds a different material.

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

#### `write_protection` items
{{ enum_table("write_protection_enum") }}

## Auxiliary section

### Field list
{{ fields_table("aux_fields", "") }}

#### Field list (SLA-specific)
{{ fields_table("aux_fields", "sla") }}

#### Vendor-specific fields
Vendor-specific fields not specified in this document are permitted for keys specified by the following table. Vendors may contact the specification authority to be assigned a key range for them to use.

| Min key | Max key | Vendor |
| --- | --- | --- |
| 65400 | 65534 | General purpose |
| 65300 | 65400 | Prusa |

The "General purpose" key region MAY be used by anyone, provided they follow the following rules:
1. Each general purpose range user MUST assign themselves a unique enough `general_purpose_range_user` value. This is done with no central authority.
1. The general purpose range MUST be used only by one user at a time, determined by the `general_purpose_range_user` field.
1. The users MUST ensure that the `general_purpose_range_user` field is set to the value assigned to them for any read or write access to the general purpose range.
1. The users MUST delete any general purpose range fields present before changing the value of `general_purpose_range_user`.
