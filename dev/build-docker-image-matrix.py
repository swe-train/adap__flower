import argparse
import json
from typing import Any, Callable

ALPINE_VERSION = "alpine3.19"
BASE_OSS = [
    {"tag": "ubuntu22.04", "version": "22.04", "file_dir": "src/docker/base/ubuntu"},
    {
        "tag": ALPINE_VERSION,
        "version": ALPINE_VERSION,
        "file_dir": "src/docker/base/alpine",
    },
]

LATEST_SUPPORTED_PYTHON_VERSIONS = "3.11"
SUPPORTED_PYTHON_VERSIONS = ["3.8", "3.9", "3.10", LATEST_SUPPORTED_PYTHON_VERSIONS]


def generate_base_matrix_item(
    flwr_version: str, python_version: str, os: dict[str, str]
) -> dict[str, Any]:
    return {
        "os": os,
        "python_version": python_version,
        "tag": f"{flwr_version}-py{python_version}-{os['tag']}",
        "flwr_version": flwr_version,
    }


def generate_base_image_matrix(
    flwr_version: str, python_versions: list[str], oss: list[dict[str, str]]
) -> list[dict[str, Any]]:
    return [
        generate_base_matrix_item(flwr_version, py, os)
        for os in oss
        for py in python_versions
    ]


def generate_binary_matrix_item(
    namespace_repository: str,
    file_dir: str,
    base_image: str,
    conditional_tags: None | Callable,
) -> dict[str, Any]:
    tags = [base_image["tag"]]
    if conditional_tags is not None:
        tags += conditional_tags(base_image) or []

    return {
        "namespace_repository": namespace_repository,
        "file_dir": file_dir,
        "base_image": base_image["tag"],
        "tags": "\n".join(tags),
    }


def generate_binary_matrix(
    namespace_repository: str,
    file_dir: str,
    base_images: str,
    conditional_tags: None | Callable = None,
    filter: None | Callable = None,
) -> list[dict[str, Any]]:
    filter = filter or (lambda _: True)

    return [
        generate_binary_matrix_item(
            namespace_repository, file_dir, image, conditional_tags
        )
        for image in base_images
        if filter(image)
    ]


def is_latest_python_alpine_image(image: dict[str, Any]) -> bool:
    return (
        image["os"]["version"] == ALPINE_VERSION
        and image["python_version"] == LATEST_SUPPORTED_PYTHON_VERSIONS
    )


arg_parser = argparse.ArgumentParser(
    description="Generate Github Docker workflow matrix"
)
arg_parser.add_argument("--flwr-version", type=str, required=True)
args = arg_parser.parse_args()

flwr_version = args.flwr_version


def on_latest_python_alpine_image(image: dict[str, Any]) -> None | list[str]:
    if is_latest_python_alpine_image(image):
        return [flwr_version]
    else:
        None


base_images = generate_base_image_matrix(
    flwr_version,
    SUPPORTED_PYTHON_VERSIONS,
    BASE_OSS,
)

binary_images = (
    generate_binary_matrix(
        "flwr/superlink",
        "src/docker/superlink",
        base_images,
        on_latest_python_alpine_image,
        is_latest_python_alpine_image,
    )
    + generate_binary_matrix(
        "flwr/supernode",
        "src/docker/supernode",
        base_images,
        on_latest_python_alpine_image,
    )
    + generate_binary_matrix(
        "flwr/serverapp",
        "src/docker/serverapp",
        base_images,
        on_latest_python_alpine_image,
    )
)

print(
    json.dumps({"base": {"images": base_images}, "binary": {"images": binary_images}})
)
