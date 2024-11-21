"""The apio context."""

# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2019 FPGAwars
# -- Author Jesús Arroyo
# -- Licence GPLv2

import sys
import json
import platform
from collections import OrderedDict
import shutil
from pathlib import Path
from typing import Optional, Dict
import click
from apio import util, env_options
from apio.profile import Profile
from apio.managers.project import Project


# ---------- RESOURCES
RESOURCES_DIR = "resources"

# ---------------------------------------
# ---- File: resources/platforms.json
# --------------------------------------
# -- This file contains  the information regarding the supported platforms
# -- and their attributes.
PLATFORMS_JSON = "platforms.json"

# ---------------------------------------
# ---- File: resources/packages.json
# --------------------------------------
# -- This file contains all the information regarding the available apio
# -- packages: Repository, version, name...
PACKAGES_JSON = "packages.json"

# -----------------------------------------
# ---- File: resources/boads.json
# -----------------------------------------
# -- Information about all the supported boards
# -- names, fpga family, programmer, ftdi description, vendor id, product id
BOARDS_JSON = "boards.json"

# -----------------------------------------
# ---- File: resources/fpgas.json
# -----------------------------------------
# -- Information about all the supported fpgas
# -- arch, type, size, packaging
FPGAS_JSON = "fpgas.json"

# -----------------------------------------
# ---- File: resources/programmers.json
# -----------------------------------------
# -- Information about all the supported programmers
# -- name, command to execute, arguments...
PROGRAMMERS_JSON = "programmers.json"

# -----------------------------------------
# ---- File: resources/distribution.json
# -----------------------------------------
# -- Information about all the supported apio and pip packages
DISTRIBUTION_JSON = "distribution.json"


# pylint: disable=too-many-instance-attributes
class ApioContext:
    """Apio context. Class for accesing apio resources and configurations."""

    def __init__(
        self,
        *,
        load_project: bool,
        project_dir: Optional[Path] = None,
    ):
        """Initializes the ApioContext object. 'project dir' is an optional
        path to the project dir, otherwise, the current directory is used.
        'load_project' indicates if project specfic context such as
        apio.ini or custom boards.json should be loaded. Some commands operate
        on project while other, such as apio drivers and apio packages,
        do not require a project.
        """

        # -- Inform as soon as possible about the list of apio env options
        # -- that modify its default behavior.
        defined_env_options = env_options.get_defined()
        if defined_env_options:
            click.secho(
                f"Active env options [{', '.join(defined_env_options)}].",
                fg="yellow",
            )

        # -- Save the load project status.
        self._load_project = load_project

        # -- Maps the optional project_dir option to a path.
        self.project_dir: Path = util.get_project_dir(project_dir)

        # -- Profile information, from ~/.apio/profile.json
        self.profile = Profile()

        # -- Read the platforms information.
        self.platforms = self._load_resource(PLATFORMS_JSON)

        # -- Determine the platform_id for this APIO session.
        self.platform_id = self._determine_platform_id(self.platforms)

        # -- Read the apio packages information
        self.all_packages = self._load_resource(PACKAGES_JSON)

        # -- Expand in place the env templates in all_packages.
        ApioContext._resolve_package_envs(self.all_packages)

        # The subset of packages that are applicable to this platform.
        self.platform_packages = self._select_packages_for_platform(
            self.all_packages, self.platform_id, self.platforms
        )

        # -- Read the boards information. Allow override files in project dir.
        self.boards = self._load_resource(BOARDS_JSON, allow_custom=True)

        # -- Read the FPGAs information. Allow override files in project dir.
        self.fpgas = self._load_resource(FPGAS_JSON, allow_custom=True)

        # -- Read the programmers information. Allow override files in project
        # -- dir.
        self.programmers = self._load_resource(
            PROGRAMMERS_JSON, allow_custom=True
        )

        # -- Read the distribution information
        self.distribution = self._load_resource(DISTRIBUTION_JSON)

        # -- Sort resources for consistency and intunitiveness.
        # --
        # -- We don't sort the all_packages and platform_packages dictionaries
        # -- because that will affect the order of the env path items.
        # -- Instead we preserve the order from the packages.json file.

        self.boards = OrderedDict(
            sorted(self.boards.items(), key=lambda t: t[0])
        )
        self.fpgas = OrderedDict(
            sorted(self.fpgas.items(), key=lambda t: t[0])
        )

        # -- If requested, load the project's apio.ini
        if load_project:
            self._project = Project(self.project_dir)
            self._project.read()

    def check_project_loaded(self):
        """Assert that context was created with project loading.."""
        assert (
            self._load_project
        ), "Apio context created without project loading."

    @property
    def project(self):
        """Property to return the project after verification that it was
        loaded."""
        self.check_project_loaded()
        return self._project

    def _load_resource(self, name: str, allow_custom: bool = False) -> dict:
        """Load the resources from a given json file
        * INPUTS:
          * Name: Name of the json file
            Use the following constants:
              * PACKAGES_JSON
              * BOARD_JSON
              * FPGAS_JSON
              * PROGRAMMERS_JSON
              * DISTRIBUTION_JSON
            * Allow_custom: if true, look first in the project dir for
              a project specific resource file of same name.
        * OUTPUT: A dictionary with the json file data
          In case of error it raises an exception and finish
        """
        # -- Try loading a custom resource file from the project directory.
        filepath = self.project_dir / name

        if filepath.exists():
            if allow_custom:
                click.secho(f"Loading project's custom '{name}' file.")
                return self._load_resource_file(filepath)

        # -- Load the stock resource file from the APIO package.
        filepath = util.get_path_in_apio_package(RESOURCES_DIR) / name
        return self._load_resource_file(filepath)

    @staticmethod
    def _load_resource_file(filepath: Path) -> dict:
        """Load the resources from a given json file path
        * OUTPUT: A dictionary with the json file data
          In case of error it raises an exception and finish
        """

        # -- Read the json file
        try:
            with filepath.open(encoding="utf8") as file:

                # -- Read the json file
                data_json = file.read()

        # -- json file NOT FOUND! This is an apio system error
        # -- It should never ocurr unless there is a bug in the
        # -- apio system files, or a bug when calling this function
        # -- passing a wrong file
        except FileNotFoundError as exc:

            # -- Display Main error
            click.secho("Apio System Error! JSON file not found", fg="red")

            # -- Display the affected file (in a different color)
            apio_file_msg = click.style("Apio file: ", fg="yellow")
            filename = click.style(f"{filepath}", fg="blue")
            click.secho(f"{apio_file_msg} {filename}")

            # -- Display the specific error message
            click.secho(f"{exc}\n", fg="red")

            # -- Abort!
            sys.exit(2)

        # -- Parse the json format!
        try:
            resource = json.loads(data_json)

        # -- Invalid json format! This is an apio system error
        # -- It should never ocurr unless some develeper has
        # -- made a mistake when changing the json file
        except json.decoder.JSONDecodeError as exc:

            # -- Display Main error
            click.secho("Apio System Error! Invalid JSON file", fg="red")

            # -- Display the affected file (in a different color)
            apio_file_msg = click.style("Apio file: ", fg="yellow")
            filename = click.style(f"{filepath}", fg="blue")
            click.secho(f"{apio_file_msg} {filename}")

            # -- Display the specific error message
            click.secho(f"{exc}\n", fg="red")

            # -- Abort!
            sys.exit(1)

        # -- Return the object for the resource
        return resource

    @staticmethod
    def _expand_env_template(template: str, package_path: Path) -> str:
        """Fills a packages env value template as they appear in packages.json.
        Currently it recognizes only a single place holder '%p' representing
        the package absolute path. The '%p" can appear only at the begigning
        of the template.

        E.g. '%p/bin' -> '/users/user/.apio/packages/drivers/bin'

        NOTE: This format is very basic but is sufficient for the current
        needs. If needed, extend or modify it.
        """

        # Case 1: No place holder.
        if "%p" not in template:
            return template

        # Case 2: The template contains only the placeholder.
        if template == "%p":
            return str(package_path)

        # Case 3: The place holder is the prefix of the template's path.
        if template.startswith("%p/"):
            return str(package_path / template[3:])

        # Case 4: Unsupported.
        raise RuntimeError(f"Invalid env template: [{template}]")

    @staticmethod
    def _resolve_package_envs(packages: Dict[str, Dict]) -> None:
        """Resolve in place the path and var value templates in the
        given packages dictionary. For example, %p is replaced with
        the package's absolute path."""

        packages_dir = util.get_packages_dir()
        for _, package_config in packages.items():

            # -- Get the package root dir.
            package_path = (
                packages_dir / package_config["release"]["folder_name"]
            )

            # -- Get the json 'env' section. We require it, even if empty,
            # -- for clarity reasons.
            assert "env" in package_config
            package_env = package_config["env"]

            # -- Expand the values in the "path" section, if any.
            path_section = package_env.get("path", [])
            for i, path_template in enumerate(path_section):
                path_section[i] = ApioContext._expand_env_template(
                    path_template, package_path
                )

            # -- Expand the values in the "vars" section, if any.
            vars_section = package_env.get("vars", {})
            for var_name, val_template in vars_section.items():
                vars_section[var_name] = ApioContext._expand_env_template(
                    val_template, package_path
                )

    def get_package_info(self, package_name: str) -> str:
        """Returns the information of the package with given name.
        The information is a JSON dict originated at packages.jsnon().
        Exits with an error message if the package is not defined.
        """
        package_info = self.platform_packages.get(package_name, None)
        if package_info is None:
            click.secho(f"Error: unknown package '{package_name}'", fg="red")
            sys.exit(1)

        return package_info

    def get_package_folder_name(self, package_name: str) -> str:
        """Returns name of the package folder, within the packages dir.
        Exits with an error message if not found."""

        package_info = self.get_package_info(package_name)

        release = package_info.get("release", {})
        folder_name = release.get("folder_name", None)
        if not folder_name:
            # -- This is a programming error, not a user error
            click.secho(
                f"Error: package '{package_name}' definition has an "
                "empty or missing 'folder_name' field.",
                fg="red",
            )
            sys.exit(1)

        return folder_name

    def get_platform_packages_lists(self) -> tuple[list, list]:
        """Get all the packages that are applicable to this platform,
        grouped as installed and not installed
        * OUTPUT:
          - A tuple of two lists: Installed and not installed packages
        """

        # -- Classify the packages in two lists
        installed_packages = []
        notinstalled_packages = []

        # -- Go though all the apio packages and add them to the installed
        # -- or uninstalled lists.
        for package_name, package_config in self.platform_packages.items():

            # -- Collect information about the package
            data = {
                "name": package_name,
                "version": None,
                "description": package_config["description"],
            }

            # -- Check if this package is installed
            if package_name in self.profile.packages:

                # -- Get the installed version
                version = self.profile.packages[package_name]["version"]

                # -- Store the version
                data["version"] = version

                # -- Store the package
                installed_packages += [data]

            # -- The package is not installed
            else:
                notinstalled_packages += [data]

        # -- If there are in the profile packages that are not in the
        # -- platform packages, add them well to the uninstalled list, as
        # -- 'unknown'. These must be some left overs, e.g. if apio is
        # -- upgraded.
        for package_name in self.profile.packages:
            if package_name not in self.platform_packages:
                data = {
                    "name": package_name,
                    "version": "Unknown",
                    "description": "Unknown deprecated package",
                }
                installed_packages += [data]

        # -- Return the packages, classified
        return installed_packages, notinstalled_packages

    def list_packages(self, installed=True, notinstalled=True):
        """Return a list with all the installed/notinstalled packages"""

        # Classify packages
        installed_packages, notinstalled_packages = (
            self.get_platform_packages_lists()
        )

        # -- Calculate the terminal width
        terminal_width, _ = shutil.get_terminal_size()

        # -- String with a horizontal line with the same width
        # -- as the terminal
        line = "─" * terminal_width
        dline = "═" * terminal_width

        if installed and installed_packages:

            # ------- Print installed packages table
            # -- Print the header
            click.secho()
            click.secho(dline, fg="green")
            click.secho("Installed packages:", fg="green")

            for package in installed_packages:
                click.secho(line)
                name = click.style(f"{package['name']}", fg="cyan", bold=True)
                version = package["version"]
                description = package["description"]

                click.secho(f"• {name} {version}")
                click.secho(f"  {description}")

            click.secho(dline, fg="green")
            click.secho(f"Total: {len(installed_packages)}")

        if notinstalled and notinstalled_packages:

            # ------ Print not installed packages table
            # -- Print the header
            click.secho()
            click.secho(dline, fg="yellow")
            click.secho("Available packages (Not installed):", fg="yellow")

            for package in notinstalled_packages:

                click.secho(line)
                name = click.style(f"• {package['name']}", fg="red")
                description = package["description"]
                click.secho(f"{name}  {description}")

            click.secho(dline, fg="yellow")
            click.secho(f"Total: {len(notinstalled_packages)}")

        click.secho("\n")

    def get_package_dir(self, package_name: str) -> Path:
        """Returns the root path of a package with given name."""

        package_folder = self.get_package_folder_name(package_name)
        package_dir = util.get_packages_dir() / package_folder

        return package_dir

    @staticmethod
    def _determine_platform_id(platforms: Dict[str, Dict]) -> str:
        """Determines and returns the platform io based on system info and
        optional override."""
        # -- Use override and get from the underlying system.
        platform_id_override = env_options.get(env_options.APIO_PLATFORM)
        if platform_id_override:
            platform_id = platform_id_override
        else:
            platform_id = ApioContext._get_system_platform_id()

        # -- Verify it's valid. This can be a user error if the override
        # -- is invalid.
        if platform_id not in platforms.keys():
            click.secho(f"Error: unknown platform id: [{platform_id}]")
            click.secho(
                "\n"
                "[Hint]: For the list of supported platforms\n"
                "type 'apio system --platforms'.",
                fg="yellow",
            )
            sys.exit(1)

        # -- All done ok.
        return platform_id

    @staticmethod
    def _select_packages_for_platform(
        all_packages: Dict[str, Dict],
        platform_id: str,
        platforms: Dict[str, Dict],
    ):
        """Given a dictionary with the packages.json packages configurations,
        returns subset dictionary with packages that are applicable to the
        this platform.
        """

        # -- Final dict with the output packages
        filtered_packages = {}

        # -- Check all the packages
        for package_name in all_packages.keys():

            # -- Get the information about the package
            release = all_packages[package_name]["release"]

            # -- This packages is available only for certain platforms.
            if "available_platforms" in release:

                # -- Get the available platforms
                available_platforms = release["available_platforms"]

                # -- Check all the available platforms
                for available_platform in available_platforms:

                    # -- Sanity check. If this fails, it's a programming error
                    # -- rather than a user error.
                    assert available_platform in platforms, (
                        f"Unknown available platform: '{available_platform}' "
                        "in package '{pkg}'"
                    )

                    # -- Match!
                    if platform_id == available_platform:

                        # -- Add it to the output dictionary
                        filtered_packages[package_name] = all_packages[
                            package_name
                        ]

            # -- Package for all the platforms
            else:

                # -- Add it to the output dictionary
                filtered_packages[package_name] = all_packages[package_name]

        # -- Update the current packages!
        return filtered_packages

    @staticmethod
    def _get_system_platform_id() -> str:
        """Return a String with the current platform:
        ex. linux_x86_64
        ex. windows_amd64"""

        # -- Get the platform: linux, windows, darwin
        type_ = platform.system().lower()
        platform_str = f"{type_}"

        # -- Get the architecture
        arch = platform.machine().lower()

        # -- Special case for windows
        if type_ == "windows":
            # -- Assume all the windows to be 64-bits
            arch = "amd64"

        # -- Add the architecture, if it exists
        if arch:
            platform_str += f"_{arch}"

        # -- Return the full platform
        return platform_str

    def is_linux(self) -> bool:
        """Returns True iff platform_id indicates linux."""
        return "linux" in self.platform_id

    def is_darwin(self) -> bool:
        """Returns True iff platform_id indicates Mac OSX."""
        return "darwin" in self.platform_id

    def is_windows(self) -> bool:
        """Returns True iff platform_id indicates windows."""
        return "windows" in self.platform_id