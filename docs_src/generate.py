from generate_common import gen_doc_file, env, Column, enum_columns, dir, out_dir
import shutil

env.globals["material_tag_columns"] = enum_columns + [
    Column(field="implies", title="Implies", transform=lambda x: ", ".join(map(lambda y: f"`{y}`", x)) if x else ""),
    Column(field="hints", title="Hints", transform=lambda x: ", ".join(map(lambda y: f"`{y}`", x)) if x else ""),
]

env.globals["material_type_columns"] = [
    Column(field="key", title="Key"),
    Column(field="abbreviation", title="Name", transform=lambda x: f"`{x}`"),
    Column(field="name", title="Full name"),
    Column(field="description", title="Description"),
]

gen_doc_file("_navbar")
gen_doc_file("_sidebar")
gen_doc_file("README")

gen_doc_file("terminology")
gen_doc_file("nfc_data_format")
gen_doc_file("nfc_technical_details")
gen_doc_file("examples")
gen_doc_file("contributing")
gen_doc_file("material_tags")
gen_doc_file("material_types")

shutil.copyfile(f"{dir}/class_diagram.svg", f"{out_dir}/class_diagram.svg")
