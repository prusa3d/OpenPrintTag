# Technical details

## 1. Used standards
- [ISO/IEC 15693-3](https://en.wikipedia.org/wiki/ISO/IEC_15693)
- [NFC Data Exchange Format (NDEF)](https://nfc-forum.org/build/specifications/data-exchange-format-ndef-technical-specification/)
- [Concise Binary Object Representation (CBOR)](https://cbor.io/)

## 2. Notes & recommendations
   1. The standard was designed with ICODE SLIX2 320 B tag in mind, but it is meant be compatible with all NFC-V tags.
      - Smaller tags might not fit all features/data the Prusa Material standard offers. It is up to the manufacturers to decide what data they want to provide in that case.
   1. We recommend to **expand the payload of the NDEF record so that the whole available memory of the NFC tag is used.**

      - The idea is that the factory can fully lock the blocks containing the NDEF  headers and would only keep the memory pool open. (Possibly write protecting  part of it as well).
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

## 3. Write protection
The OpenPrintTag standard offers the following options also considers ways to prevent the tags from being overwritten by malicious actors.

### 3.1 Protecting the auxiliary region
Auxiliary region cannot be reasonably write-protected, because it is intended to be written to by the printers and that needs to be plug-an-play for user comfort.
Therefore it can contain invalid data when a customer first brings it from the shop (because anyone could have written anything to it).

To remedy this issue, the auxiliary section has the `workgroup` field specified. Devices accessing the auxiliary region SHOULD have a workgroup specified (generated randomly by default, but can be changed by the user so that multiple devices have the same workgroup).
When a tag is detected by the device and the workgroup doesn't match, the device SHOULD offer wiping the auxiliary region. The tag workgroup field SHOULD then be set to the device wogrkoup (even if the user decided not to wipe the region, to prevent repeated prompts).

As a result, the user should be alerted to wipe the auxiliary region on first usage of the filament and then, because the workgroup is the same, there should be no further obstructions.

### 3.2 Protecting the rest of the tag
The rest of the tag (NDEF header, meta region, main region) can be protected more strongly, because it is not expected to be changed regularily (just for refills or reusing the tag). The form of protection is indicated by the `write_protection` field in the main section.

* The locking mechanisms work on the block level, so we recommend **aligning the regions with the NFC tag blocks**.

#### 3.2.1 `write_protection` items
{{ enum_table("write_protection_enum") }}

#### 3.2.2 `irreversible` protection
The irreversible locking can be achiaved using the `LOCK BLOCK` command on the whole tag (except the auxiliary region). We do not recommend this, as it prevents reuse of the NFC tag.

#### 3.2.3 `protect_page_unlockable` protection (SLIX2-specific)
Using `protect_page_unlockable` is the recommended way of protecting the tag. It is based on the `PROTECT PAGE` command, which is a SLIX2-specific command.

1. The tag is write-protected using the `PROTECT PAGE` page command.
   - The protection SHOULD be marked in byte 1 of the Capability Container (CC)
1. The `PROTECT PAGE` on SLIX2 splits the tag memory into two arbitrarily-sized parts and offers setting up different protections on each. So the tag should be arranged in such way that:
   1. The NDEF header and meta and main regions are together on the first part with write protection enabled.
   1. The auxiliary region is on the second part with write protection disabled.
1. The main region can be written to when a correct write password is set using `SET PASSWORD`.
1. The main region can be fully unlocked by a correct `PROTECT_PAGE` command (resetting the protection flags) when the correct write password is set.
1. The password SHALL be randomly generated for each package instance.
1. The password SHOULD be located somewhere on the container, in such way that it is not accessible without unpacking the container.
   - We recommend encoding the password in a QR code in an URL. In this case, a brand-specific pattern matching regex should be defined how to parse the password from the URL.
   - The password can also be in the form of a user-readable text.
