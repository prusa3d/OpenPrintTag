from generate_common import gen_doc_file, env, Column, enum_columns

env.globals["material_tag_columns"] = enum_columns + [
    Column(field="implies", title="Implies", transform=lambda x: ", ".join(map(lambda y: f"`{y}`", x)) if x else ""),
    Column(field="hints", title="Hints", transform=lambda x: ", ".join(map(lambda y: f"`{y}`", x)) if x else ""),
]


gen_doc_file("_navbar")
gen_doc_file("README")

gen_doc_file("terminology")
gen_doc_file("nfc_data_format")
gen_doc_file("nfc_technical_details")
gen_doc_file("examples")
gen_doc_file("contributing")
gen_doc_file("material_tags")
