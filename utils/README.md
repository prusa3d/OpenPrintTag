# OpenPrintTag utilities

This directory contains an example implementation of the OpenPrintTag data format in Python. Some scripts work as CLI applications, you can check their [example usage here](https://specs.openprinttag.org/#/examples).

* `nfc_initialize.py` is both a CLI application and a Python module and can be used for initializing a blank NFC tag in the OpenPrintTag data format.
* `rec_update.py` is a CLI application for updating binary data on a tag. It takes an initialized tag binary data on stdin and outputs the updated data to the stdout.
* `rec_info.py` is a CLI application for parsing tag binary tada passed to the stdin. It can output the data in a human (and machine) readable form, show tag usage statics, and so on.
* `record.py` is a python module for reading and manipulating initialized tag data. It is used by `rec_info.py` and `rec_update.py`
* `opt_check.py` is both a CLI application and a Python module, intended for inferring and validating the data on the semantic level.
