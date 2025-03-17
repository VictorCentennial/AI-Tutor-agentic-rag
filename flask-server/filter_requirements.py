#!/usr/bin/env python3
"""
Script to filter requirements.txt for Docker compatibility
"""
import sys

# Packages to exclude in Docker environment
EXCLUDE_PACKAGES = [
    "pywin32",
    "python-magic-bin",
    "pypiwin32",
    "win32",
]


def filter_requirements(input_file, output_file):
    """Filter out Windows-specific packages from requirements file"""
    with open(input_file, "r") as f_in:
        requirements = f_in.readlines()

    filtered = []
    for req in requirements:
        # Check if line contains any excluded package
        if not any(pkg in req.lower() for pkg in EXCLUDE_PACKAGES):
            filtered.append(req)

    with open(output_file, "w") as f_out:
        f_out.writelines(filtered)

    print(f"Created filtered requirements file: {output_file}")
    print(f"Excluded {len(requirements) - len(filtered)} packages")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        filter_requirements(sys.argv[1], sys.argv[2])
    else:
        filter_requirements("requirements.txt", "requirements-docker.txt")
