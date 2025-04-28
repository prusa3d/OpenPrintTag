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

## Write protection
The Prusa NFC standards offers these options also considers ways to prevent the tags from being overwritten by malicious actors.

### Protecting the auxiliary region
Auxiliary region cannot be reasonably write-protected, because it is intended to be written to by the printers and that needs to be plug-an-play for user comfort.
Therefore it can contain invalid data when a customer first brings it from the shop (because anyone could have written anything to it).

To remedy this issue, the auxiliary section has the `workgroup` field specified. Each printer has a workgroup specified (generated randomly by default, but can be changed by the user so that multiple printers have the same workgroup).
When the tag is detected by a printer and the workgroup doesn't match, the printer should offer wiping the auxiliary region (and/or setting the correct workgroup).

As a result, the user should be alerted to wipe the auxiliary region on first usage of the filament and then, because the workgroup is the same, there should be no further obstructions.

### Protecting the rest of the tag
The rest of the tag (NDEF header, meta region, main region) can be protected more strongly, because it is not expected to be changed regularily (just for refills or reusing the tag). The form of protection is indicated by the `write_protection` field in the main section.

* The locking mechanisms work on the block level, so we recommend **aligning the regions with the NFC tag blocks**.

#### `write_protection` items
{{ enum_table("write_protection_enum") }}

##### `irreversible`
The irreversible locking can be achiaved using the `LOCK BLOCK` command on the whole tag (except the auxiliary region). We do not recommend this, as it prevents reuse of the NFC tag.

##### `protect_page_unlockable` (SLIX2-specific)
Using `protect_page_unlockable` is the recommended way of protecting the tag. It is based on the `PROTECT PAGE` command, which is a SLIX2-specific command.

- The tag is write-protected using the `PROTECT PAGE` page command. The `PROTECT PAGE` on SLIX2 splits the tag memory into two arbitrarily-sized parts and offers setting up different protections on each. So the tag should be arranged in such way that:
   - The NDEF header and meta and main regions should be together on the first part with write protection enabled.
   - The auxiliary region should be on the second part with write protection disabled.
- The main region can be written to when a correct write password is set using `SET PASSWORD`.
- The main region can be fully unlocked by a correct `PROTECT_PAGE` command (resetting the protection flags) when the correct write password is set.
- The password should be randomly generated for each package instance.
- The password should be located somewhere on the container, in such way that it is not accessible without unpacking the container.
   - We recommend encoding the password in a QR code in an URL. In this case, a brand-specific pattern matching regex should be defined how to parse the password from the URL.
   - The password can also be in the form of a user-readable text.
