import shutil
import os
import jinja2
import subprocess
import itertools

from vars import *

# Re-create output directory
shutil.rmtree(out_dir, ignore_errors=True)
os.mkdir(out_dir)

# Copy the docsify index.html
shutil.copyfile(f"{dir}/index.html", f"{out_dir}/index.html")

# Set up jinja
env = jinja2.Environment(loader=jinja2.FileSystemLoader(dir))
args = {}

# Tables support
from tables import *

def region_type_transform(cell, row):
    result = cell
    if "max_length" in row:
        result = f"{result}:{row['max_length']}"

    return f"`{result}`"

cbor_region_columns = [
    Column(field="name", title="Name", transform=lambda x: f"`{x}`"),
    Column(field="required", title="R", transform=required_transform),
    Column(field="key", title="Key"),
    Column(field="type", title="Type", transform_ext=region_type_transform),
    Column(field="unit", title="Unit"),
    Column(field="example", title="Example"),
    Column(field="description", title="Description"),
]

enum_columns = [
    Column(field="name", title="Name", transform=lambda x: f"`{x}`"),
    Column(field="key", title="Key"),
    Column(field="description", title="Description"),
]

env.globals["fields_table"] = lambda file, category=None: generate_table(f"{data_dir}/{file}.yaml", cbor_region_columns, lambda row: (category is None) or row.get("category", "") == category)
env.globals["enum_table"] = lambda file: generate_table(f"{data_dir}/{file}.yaml", enum_columns)

# Examples support


def show_example(prompt, language="yaml"):
    r = io.StringIO("")

    nice_prompt = prompt.replace(">", "").replace(" | ", "\n> | ")
    r.write(f"> ```bash\n>{nice_prompt}\n> ```\n\n")

    output = subprocess.run(prompt.replace(">", f"python3 {utils_dir}/"), shell=True, stdout=subprocess.PIPE, check=False, cwd=dir)

    r.write(f"```{language}\n{output.stdout.decode()}\n```\n")

    return r.getvalue()


env.globals["show_example"] = show_example


def show_file(file, language="yaml"):
    r = io.StringIO("")
    r.write(f"> ```bash\n> cat {file}\n> ```\n\n")

    with open(f"{dir}/{file}", "r") as f:
        r.write(f"```{language}\n{f.read()}\n```\n")

    return r.getvalue()


env.globals["show_file"] = show_file


# Other variables
env.globals["repo"] = repo

# Generate documentation files
def gen_doc_file(source_file):
    with open(f"{out_dir}/{source_file}.md", "w") as f:
        f.write(env.get_template(f"{source_file}.md").render(args))


gen_doc_file("_navbar")
gen_doc_file("README")

gen_doc_file("terminology")
gen_doc_file("nfc_data_format")
gen_doc_file("examples")
