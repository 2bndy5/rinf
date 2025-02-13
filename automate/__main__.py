from argparse import ArgumentParser
import os
from subprocess import run
import time
from typing import List


def get_cli_parser() -> ArgumentParser:
    parser = ArgumentParser(description="automation script for some common tasks")
    sub_cmds = parser.add_subparsers(required=True, dest="sub_cmd")

    sub_cmds.add_parser(
        "cargokit-update",
        description="Update Cargokit from git source",
    )

    prep_app = sub_cmds.add_parser(
        "prepare-app",
        description="prepare an app for building/running",
    )
    prep_app.add_argument(
        "app",
        choices=["test", "user", "example"],
        help="which app to prepare?",
    )
    return parser


def replace_text_in_file(filepath: str, change_from: str, change_to: str):
    with open(filepath, mode="r", encoding="utf-8") as file:
        content: str = file.read()
    content = content.replace(change_from, change_to)
    with open(filepath, mode="w", encoding="utf-8") as file:
        file.write(content)


def prepare_web_target():
    """Enable the web target, since it's not enabled by default."""

    replace_text_in_file(
        "native/hub/src/lib.rs",
        "// use tokio_with_wasm::alias as tokio;",
        "use tokio_with_wasm::alias as tokio;",
    )
    replace_text_in_file(
        "native/hub/Cargo.toml",
        "# tokio_with_wasm",
        "tokio_with_wasm",
    )
    replace_text_in_file(
        "native/hub/Cargo.toml",
        "# wasm-bindgen",
        "wasm-bindgen",
    )


def retry_for(command: List[str], attempts=5):
    """
    Retry the command in case of failure,
    possibly due to GitHub API rate limiting
    associated with the 'protoc_prebuilt' crate.
    """

    result = run(command)
    while result.returncode != 0 and attempts > 0:
        print("Retrying", f"`{' '.join(command)}`", "in 60 seconds...")
        time.sleep(60)
        result = run(command)
        attempts -= 1
    result.check_returncode()


def append_gitignore(new_path: str):
    filepath = ".gitignore"
    with open(filepath, mode="r", encoding="utf-8") as file:
        content: str = file.read()
    content += f"\n/{new_path}/"
    with open(filepath, mode="w", encoding="utf-8") as file:
        file.write(content)


parser = get_cli_parser()
cli_options = parser.parse_args()

if cli_options.sub_cmd == "cargokit_update":
    print("Updating CargoKit...")
    command = ["git", "subtree", "pull"]
    command.extend(["--prefix", "flutter_package/cargokit"])
    command.append("https://github.com/irondash/cargokit.git")
    command.append("main")
    run(command, check=True)

elif cli_options.sub_cmd == "prepare-app" and hasattr(cli_options, "app"):
    if cli_options.app == "test":
        append_gitignore("test_app")

        command = "flutter create test_app".split()
        run(command, check=True)

        os.chdir("./test_app/")

        command = "dart pub add \"rinf:{'path':'../flutter_package'}\"".split()
        run(command, check=True)
        command = "rinf template".split()
        retry_for(command)

        os.remove("Cargo.toml")

        prepare_web_target()

        os.chdir("../")

        replace_text_in_file(
            "Cargo.toml",
            "flutter_package/example/native/*",
            "test_app/native/*",
        )

    elif cli_options.app == "user":
        append_gitignore("user_app")

        command = "flutter create user_app".split()
        run(command, check=True)

        os.chdir("./user_app/")

        command = "flutter pub add rinf".split()
        run(command, check=True)
        command = "rinf template".split()
        retry_for(command)

        os.remove("Cargo.toml")

        prepare_web_target()

        os.chdir("../")

        replace_text_in_file(
            "Cargo.toml",
            "flutter_package/example/native/*",
            "user_app/native/*",
        )
        replace_text_in_file(
            "Cargo.toml",
            'rinf = { path = "./rust_crate" }',
            "",
        )

    elif cli_options.app == "example":
        print("Preparing example app")
        os.chdir("./flutter_package/example")

        command = "rinf message".split()
        retry_for(command)
