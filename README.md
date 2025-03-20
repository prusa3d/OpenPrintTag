# Prusa Material Data Format

This repository contains specification, documentation and utility scripts for the Prusa Material Data Format.

**This is a "raw" repository, you can access the compiled documentation here:**
* https://prusamaterials.danol.cz (Github pages will be used once we go public)
* User: prusa
* Password: tvrdimzenejsem

To generate documentation (to the `docs` directory), run:
```python
pip3 install -r requirements.py
sh generate_docs.sh
```

Then, to view it, you can:
```
cd docs
python3 -m http.server
```
and open your browser on `127.0.0.1:8000`
