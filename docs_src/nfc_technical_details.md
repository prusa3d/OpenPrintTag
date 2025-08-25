# Technical details

## Used standards
- [ISO/IEC 15693-3](https://en.wikipedia.org/wiki/ISO/IEC_15693)
- [NFC Data Exchange Format (NDEF)](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/)
- [Concise Binary Object Representation (CBOR)](https://cbor.io/)

## Notes & recommendations
   1. The standard was designed with ICODE SLIX2 320 B tag in mind, but it should be compatible with all NFC-V tags.
      - Smaller tags might not fit all features/data the Prusa Material standard offers. It is up to the manufacturers to decide what data they want to provide in that case.
   1. **The NDEF record shall not be split into multiple NDEF record chunks.**
      - Splitting the record would break the "virtual space" of the payload and would complicate implementation.
   1. We recommend to **expand the payload of the NDEF record so that the whole available memory of the NFC tag is used.**
      - The idea is that the factory can fully lock the blocks containing the NDEF  headers and would only the memory pool open. (Possibly write protecting  part of it as well).
      - Part of the memory pool is auxiliary section, which we want to be able to write to without having to edit other structures/shuffle things around.
   1. The meta section allows the manufacturers to configure the payload structure so that it fits their purposes and the used NFC tag specifics:
      1. The auxiliary region can be adjusted or even omitted, based on the NFC tag available memory.
         - It is not specified that the auxiliary region must be after the main region. Auxiliary region can possibly be located **before** the main region, if the meta section says so. We however recommend **putting the main region before the auxiliary region**, so that it can be protected together with the NDEF header.
   1. **AFI**: We recommend setting the AFI register to 0 and locking/password protecting it.
   1. **DSFID**: The DSFID register is reserved for future use. It shall be set to 0 and locked/password protected.
   1. **EAS**: Implementing EAS is up to each manufacturer discretion. We again recommend locking/password protecting it.
   1. The specification was written in such way so that it wouldn't need explicit versioning.
      - New keys can easily be introduced without breaking backwards compatibility.
      - Deprecated keys will never be reused.
      - If there would be substantial changes to the standard that would break backwards compatibility, a new MIME type will be used for the new format.

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
