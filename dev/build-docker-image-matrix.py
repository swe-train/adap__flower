import argparse
import json


BASE_OSS = [
    {"tag": "ubuntu22.04", "version": "22.04", "file_dir": "src/docker/base/ubuntu"},
    {
        "tag": "alpine3.19",
        "version": "alpine3.19",
        "file_dir": "src/docker/base/alpine",
    },
]

LATEST_SUPPORTED_PYTHON_VERSIONS = "3.11"
SUPPORTED_PYTHON_VERSIONS = ["3.8", "3.9", "3.10", LATEST_SUPPORTED_PYTHON_VERSIONS]


def generate_base_matrix_item(flwr_version, python_version, os):
    return {
        "os": os,
        "python_version": python_version,
        "tag": f"{flwr_version}-py{python_version}-{os['tag']}",
        "flwr_version": flwr_version,
    }


def generate_base_image_matrix(flwr_version, python_versions, oss):
    return [
        generate_base_matrix_item(flwr_version, py, os)
        for os in oss
        for py in python_versions
    ]


def generate_matrix_item(file_dir, base_image, conditional_tags):
    tags = [base_image["tag"]]
    if conditional_tags is not None:
        tags + (conditional_tags(base_image) or [])

    return {
        "file_dir": file_dir,
        "base_image": base_image["tag"],
        "tags": "\n".join(tags),
    }


def generate_matrix(
    file_dir,
    base_images,
    conditional_tags=None,
    filter=None,
):
    filter = filter or (lambda image: True)

    return [
        generate_matrix_item(file_dir, image, conditional_tags)
        for image in base_images
        if filter(image)
    ]


def is_latest_python_alpine_image(image):
    return (
        image["os"]["version"] == "alpine3.19"
        and image["python_version"] == LATEST_SUPPORTED_PYTHON_VERSIONS
    )


arg_parser = argparse.ArgumentParser(description="Generate GitHub Docker image matrix")
arg_parser.add_argument("--flwr-version", type=str, required=True)
args = arg_parser.parse_args()

flwr_version = args.flwr_version


def on_latest_python_alpine_image(image):
    if is_latest_python_alpine_image(image):
        return [flwr_version]
    else:
        None


base_images = generate_base_image_matrix(
    flwr_version,
    SUPPORTED_PYTHON_VERSIONS,
    BASE_OSS,
)

print(
    json.dumps(
        {
            "base": {"images": base_images},
            "superlink": {
                "images": generate_matrix(
                    "src/docker/superlink",
                    base_images,
                    on_latest_python_alpine_image,
                    is_latest_python_alpine_image,
                )
            },
            "supernode": {
                "images": generate_matrix(
                    "src/docker/supernode",
                    base_images,
                    on_latest_python_alpine_image,
                )
            },
            "serverapp": {
                "images": generate_matrix(
                    "src/docker/serverapp",
                    base_images,
                    on_latest_python_alpine_image,
                )
            },
        }
    )
)
