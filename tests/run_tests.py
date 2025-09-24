import subprocess
import sys
import yaml
from pathlib import Path

tests_dir = Path(__file__).parent
root_dir = tests_dir.parent
utils_dir = root_dir / "utils"


# Runs nfc_initialize & nfc_update utilities and checks their result, output
def utils_test(init_args: list[str] = None, update_args: list[str] = None, info_args: list[str] = None, expect_success: bool = True, expected_info_fn: str | None = None):
    all_args = locals()

    class UtilFailure(Exception):
        def __init__(self, code, stderr):
            self.code = code
            self.stderr = stderr

    def run_util(util: str, args: list[str] = [], input=None):
        proc_args = ["python3", str(root_dir / "utils" / f"{util}.py")] + args
        print(f"  Running {proc_args}")
        proc = subprocess.run(args=proc_args, input=input, capture_output=True, check=False, cwd=tests_dir)

        if proc.returncode != 0:
            raise UtilFailure(proc.returncode, proc.stderr)

        return proc.stdout

    print(f"Testing {all_args}")

    try:
        if init_args is not None:
            binary_output = run_util("nfc_initialize", init_args)
        else:
            assert False

        if update_args is not None:
            binary_output = run_util("rec_update", args=update_args, input=binary_output)

        if info_args is not None:
            info_output = run_util("rec_info", args=info_args, input=binary_output)

        if expected_info_fn is not None:
            print(f"  Comparing rec_info against '{expected_info_fn}'")
            with open(expected_info_fn, "rb") as f:
                expected_info = f.read()

            if info_output != expected_info:
                print("EXPECTED INFO\n=====================\n", expected_info.decode())
                print("ACTUAL INFO\n=======================\n", info_output.decode())
                raise "Info output does not match"

        assert expect_success, "Test should have failed"

    except UtilFailure as e:
        if expect_success:
            print(f"Unexpected return code {e.code}")
            print(e.stderr.decode())
            sys.exit(1)

    print("  Test OK")


# Check that files validate_XX.yaml generate valid tags
for file in tests_dir.glob("validate/*.yaml"):
    utils_test(
        init_args=["--size=316", "--aux-region=32", "--ndef-uri=https://3dtag.org/s/334c54f088"],
        update_args=[str(file)],
        info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    )

# Run encode/decode tests
for file in tests_dir.glob("encode_decode/*_input.yaml"):
    fn_base = str(file).removesuffix("_input.yaml")
    fn_info = f"{fn_base}_info.yaml"

    with open(fn_info, "r") as f:
        uri = yaml.safe_load(f)["uri"]

    utils_test(
        init_args=["--size=316", "--aux-region=32", "--ndef-uri", uri],
        update_args=[str(file)],
        info_args=["--validate", "--extra-required-fields=sample_requirements.yaml", "--show-all"],
        expected_info_fn=fn_info,
    )


# Check that basic required fields checking works
utils_test(
    init_args=["--size=316", "--aux-region=32"],
    update_args=["specific/missing_required_fields.yaml"],
    info_args=["--validate"],
    expect_success=False,
)

# Check that -extra-required-fields works
utils_test(
    init_args=["--size=316", "--aux-region=32"],
    update_args=["specific/missing_sample_requirements.yaml"],
    info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    expect_success=False,
)
