# OpenPrintTag

The OpenPrintTag project aims to:

1. Specify relevant properties of 3D printing materials (FFF, SLA, ...) and define their standardized terminology, units and data types.
1. Define a data format for NFC tags – storing information about materials on their packages (filament spools, resin containers, ...).

### Site map

* [Terminology](terminology.md)
* [**Format specification for NFC tags**](nfc_data_format.md) (static & dynamic information)
* Format specification for QR codes (static information only) – TBD
* [Examples](examples.md)

### Use cases for the data tags

1. Automation/user comfort
	 - When a user loads a filament in the printer, the printer can scan the tag for material information (material type, color, temperatures, ...) automatically.
2. Material usage tracking (dynamic information)
	 - Printers can use the data tags to monitor material usage.
	 	- The data can be used to warn the user when there is not enough material to start a print.
3. Inventory management
	 - Having uniquely identifiable data tag on every package enables more efficient and automated inventory management for warehouses or print farms.
