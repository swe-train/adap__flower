"""
Usage: python dev/build-docker-image-matrix.py --flwr-version <flower version e.g. 1.8.0>
"""

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Any, Callable, Dict, List, Optional


class DistroName(str, Enum):
    ALPINE = "alpine"
    UBUNTU = "ubuntu"


@dataclass
class Distro:
    name: "DistroName"
    version: str


BASE_DISTROS = [
    Distro(DistroName.UBUNTU, "22.04"),
    Distro(DistroName.ALPINE, "3.19"),
]

LATEST_SUPPORTED_PYTHON_VERSION = "3.11"
SUPPORTED_PYTHON_VERSIONS = [
    "3.8",
    "3.9",
    "3.10",
    LATEST_SUPPORTED_PYTHON_VERSION,
]

DOCKERFILE_ROOT = "src/docker"


@dataclass
class BaseImage:
    distro: Distro
    python_version: str
    namespace_repository: str
    file_dir: str
    tag: str
    flwr_version: str


def new_base_image(
    flwr_version: str, python_version: str, distro: Distro
) -> Dict[str, Any]:
    return BaseImage(
        distro,
        python_version,
        "flwr/base",
        f"{DOCKERFILE_ROOT}/base/{distro.name}",
        f"{flwr_version}-py{python_version}-{distro.name}{distro.version}",
        flwr_version,
    )


def generate_base_images(
    flwr_version: str, python_versions: List[str], distros: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    return [
        new_base_image(flwr_version, python_version, distro)
        for distro in distros
        for python_version in python_versions
    ]


@dataclass
class BinaryImage:
    namespace_repository: str
    file_dir: str
    base_image: str
    tags: List[str]


def new_binary_image(
    name: str,
    base_image: BaseImage,
    tags_fn: Optional[Callable],
) -> Dict[str, Any]:
    tags = []
    if tags_fn is not None:
        tags += tags_fn(base_image) or []

    return BinaryImage(
        f"flwr/{name}",
        f"{DOCKERFILE_ROOT}/{name}",
        base_image.tag,
        "\n".join(tags),
    )


def generate_binary_images(
    name: str,
    base_images: List[BaseImage],
    tags_fn: Optional[Callable] = None,
    filter: Optional[Callable] = None,
) -> List[Dict[str, Any]]:
    filter = filter or (lambda _: True)

    return [
        new_binary_image(name, image, tags_fn) for image in base_images if filter(image)
    ]


def is_latest_python_alpine_image(image: BaseImage) -> bool:
    return (
        image.distro.name == DistroName.ALPINE
        and image.distro.version == "3.19"
        and image.python_version == LATEST_SUPPORTED_PYTHON_VERSION
    )


def tag_latest_with_flwr_version(image: BaseImage) -> List[str]:
    if is_latest_python_alpine_image(image):
        return [image.tag, image.flwr_version]
    else:
        return [image.tag]


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Generate Github Docker workflow matrix"
    )
    arg_parser.add_argument("--flwr-version", type=str, required=True)
    args = arg_parser.parse_args()

    flwr_version = args.flwr_version

    # ubuntu and alpine base images for each supported python version
    base_images = generate_base_images(
        flwr_version,
        SUPPORTED_PYTHON_VERSIONS,
        BASE_DISTROS,
    )

    binary_images = (
        # ubuntu and alpine images for the latest supported python version
        generate_binary_images(
            "superlink",
            base_images,
            tag_latest_with_flwr_version,
            lambda image: image.python_version == LATEST_SUPPORTED_PYTHON_VERSION,
        )
        # ubuntu and alpine images for each supported python version
        + generate_binary_images(
            "supernode",
            base_images,
            tag_latest_with_flwr_version,
        )
        # ubuntu and alpine images for each supported python version
        + generate_binary_images(
            "serverapp",
            base_images,
            tag_latest_with_flwr_version,
        )
    )

    # {
    #     "base": {
    #         "images": [
    #             {
    #                 "distro": {
    #                     "name": "ubuntu",
    #                     "version": "22.04"
    #                 },
    #                 "python_version": "3.8",
    #                 "namespace_repository": "flwr/base",
    #                 "file_dir": "src/docker/base/ubuntu",
    #                 "tag": "1.8.0-py3.8-ubuntu22.04",
    #                 "flwr_version": "1.8.0"
    #             },
    #             ...
    #         ]
    #     },
    #     "binary": {
    #         "images": [
    #             {
    #                 "namespace_repository": "flwr/superlink",
    #                 "file_dir": "src/docker/superlink",
    #                 "base_image": "1.8.0-py3.11-alpine3.19",
    #                 "tags": "1.8.0-py3.11-alpine3.19\n1.8.0"
    #             },
    #             ...
    #         ]
    #     }
    # }
    print(
        json.dumps(
            {
                "base": {"images": list(map(lambda image: asdict(image), base_images))},
                "binary": {
                    "images": list(map(lambda image: asdict(image), binary_images))
                },
            }
        )
    )
