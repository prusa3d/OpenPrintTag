import subprocess
import sys
from pathlib import Path

tests_dir = Path(__file__).parent
root_dir = tests_dir.parent
utils_dir = root_dir / "utils"


# Runs nfc_initialize & nfc_update utilities and checks their result, output
def utils_test(init_args: list[str] = None, update_args: list[str] = None, info_args: list[str] = None, expect_success=True):
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
            raise UtilFailure(proc.returncode, proc.stderr.decode())

        return proc.stdout

    print(f"Testing {all_args}")

    output = None

    try:
        if init_args is not None:
            binary_output = run_util("nfc_initialize", init_args)
        else:
            assert False

        if update_args is not None:
            binary_output = run_util("rec_update", args=update_args, input=binary_output)

        if info_args is not None:
            info_output = run_util("rec_info", args=info_args, input=binary_output)

        assert expect_success, "Test should have failed"

    except UtilFailure as e:
        if expect_success:
            print(f"Unexpected return code {e.proc.returncode}")
            print(e.proc.stderr.decode())
            sys.exit(1)

    print("  Test OK")


# Check that files validate_XX.yaml generate valid tags
for file in tests_dir.glob("validate_*.yaml"):
    utils_test(
        init_args=["--size=316", "--aux-region=32", "--ndef-uri=https://3dtag.org/s/334c54f088"],
        update_args=[str(file)],
        info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    )


# Check that basic required fields checking works
utils_test(
    init_args=["--size=316", "--aux-region=32"],
    update_args=["missing_required_fields.yaml"],
    info_args=["--validate"],
    expect_success=False,
)

# Check that -extra-required-fields works
utils_test(
    init_args=["--size=316", "--aux-region=32"],
    update_args=["missing_sample_requirements.yaml"],
    info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    expect_success=False,
)
