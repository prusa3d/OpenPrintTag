# Terminology

## Brand
> For example: Prusament

Brand/manufacturer of materials, containers and possibly other relevant items.

Brands can have public keys for signing various information about the materials.

## Material type
> For example: PLA, PETG, ...

## Material
> For example: Prusament PLA Galaxy Black

Specific material from a specific manufacturer.

Properties:
- Brand (Prusament)
- Name (PLA Galaxy Black)
- Material type (PLA)
- Color (#000000)
- Printing parameters

## Material color
> For example: Galaxy Black

Specifies the looks and feel of the filament.

Properties:
- Color (RGB/RAL/Pantone/...)
- Transmission distance
- Tags (matte, glitter, rainbow, conductive, ...).

## Material container
> For example: Prusament 1kg filament spool

- FDM: Also called "Filament spool type" or "Filament material container"

Container type/shape the materials are stored in/on.

Properties:
- Empty weight

## Material package
> For example: [1 kg Prusament PLA Galaxy Black 1,75 mm](https://www.prusa3d.com/cs/produkt/prusament-pla-prusa-galaxy-black-1kg/)

A specific material put in a specific container.

Properties:
- Material
- Container
- (FDM) Diameter, tolerance


## Material package instance
> Example: That 1kg Prusament PLA Galaxy Black 1,75 mm that you have at home on your table

A single specific spool of filament.

Properties:
- Unique ID
- Material package
- Batch ID
- Manufactured date
- Signature

And possibly some dynamic data:
- Remaining material
