import subprocess
import sys
import yaml
from pathlib import Path

tests_dir = Path(__file__).parent
root_dir = tests_dir.parent
utils_dir = root_dir / "utils"

logs_dir = tests_dir / "logs"
logs_dir.mkdir(exist_ok=True)


# Runs nfc_initialize & nfc_update utilities and checks their result, output
def utils_test(init_args: list[str] = None, update_args: list[str] = None, info_args: list[str] = None, expect_success: bool = True, expected_info_fn: str | None = None, expected_data_fn: str | None = None):
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

        if expected_data_fn is not None:
            print(f"  Comparing rec_ibinary datanfo against '{expected_data_fn}'")
            with open(expected_data_fn, "rb") as f:
                expected_data = f.read()
                if binary_output != expected_data:
                    log_fn = logs_dir / f"{Path(expected_data_fn).name}.actual"
                    with open(log_fn, "wb") as f2:
                        f2.write(binary_output)

                    raise Exception(f"Binary data do not match. Actual output stored to {log_fn}")

        if info_args is not None:
            info_output = run_util("rec_info", args=info_args, input=binary_output)

        if expected_info_fn is not None:
            print(f"  Comparing rec_info against '{expected_info_fn}'")
            with open(expected_info_fn, "rb") as f:
                expected_info = f.read()

            if info_output != expected_info:
                log_fn = logs_dir / f"{Path(expected_info_fn).name}.actual"
                with open(log_fn, "w") as f2:
                    f2.write(info_output)

                raise Exception(f"Info output does not match. Actual output stored to {log_fn}")

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
        init_args=["--size=312", "--aux-region=32", "--ndef-uri=https://3dtag.org/s/334c54f088"],
        update_args=[str(file)],
        info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    )

# Run encode/decode tests
for file in tests_dir.glob("encode_decode/*_input.yaml"):
    fn_base = str(file).removesuffix("_input.yaml")
    fn_info = f"{fn_base}_info.yaml"

    with open(fn_info, "r") as f:
        uri = yaml.safe_load(f)["uri"]

    utils_test(init_args=["--size=312", "--aux-region=32", "--ndef-uri", uri], update_args=[str(file)], info_args=["--validate", "--extra-required-fields=sample_requirements.yaml", "--show-all"], expected_info_fn=fn_info, expected_data_fn=f"{fn_base}_data.bin")


# Check that basic required fields checking works
utils_test(
    init_args=["--size=312", "--aux-region=32"],
    update_args=["specific/missing_required_fields.yaml"],
    info_args=["--validate"],
    expect_success=False,
)

# Check that -extra-required-fields works
utils_test(
    init_args=["--size=312", "--aux-region=32"],
    update_args=["specific/missing_sample_requirements.yaml"],
    info_args=["--validate", "--extra-required-fields=sample_requirements.yaml"],
    expect_success=False,
)
