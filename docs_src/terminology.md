# Terminology
The OpenPrintTag format is based on the following entity model (not all fields are present):

<img src="class_diagram.svg" style="max-width: 500px; max-height: 500px;"/>

1. `Material` represents a material with some color and properties.
    1. For example "Prusament PLA Prusa Galaxy Black".
1. `MaterialType` is used to categorize materials into broad, strictly and universally defined categories.
    1. For FFF, base polymers are used for the categorization.
    1. SLA resins are not clearly categorizable, so they don't use `MaterialType`.
1. `MaterialPackage` represents a material that is packaged in some quantity (in case of FFF, the material is also extruded with a specific diameter) and put in a container.
    1. For example [Prusament PLA Prusa Galaxy Black 1kg](https://www.prusa3d.com/cs/produkt/prusament-pla-prusa-galaxy-black-1kg/).
1. `MaterialPackageInstance` represents a single specific spool of filament (or a single specific bottle of resin in case of SLA)
    1. For example [this specific spool of PLA Prusa Galaxy Black](https://prusament.com/spool/?spoolId=eb8881e3e0).
1. `MaterialContainer` represents a container the material is stored in in `MaterialPackage`. For filaments, this would be a spool, for resins, this would be a bottle.
    1. For example "Prusament 1kg spool"
