"""Revanced Parser."""
from subprocess import PIPE, Popen
from time import perf_counter
from typing import List

from loguru import logger

from src.app import APP
from src.config import RevancedConfig
from src.exceptions import PatchingFailed
from src.patches import Patches
from src.utils import possible_archs


class Parser(object):
    """Revanced Parser."""

    CLI_JAR = "-jar"
    APK_ARG = "-a"
    PATCHES_ARG = "-b"
    INTEGRATIONS_ARG = "-m"
    OUTPUT_ARG = "-o"
    KEYSTORE_ARG = "--keystore"
    OPTIONS_ARG = "--options"

    def __init__(self, patcher: Patches, config: RevancedConfig) -> None:
        self._PATCHES: List[str] = []
        self._EXCLUDED: List[str] = []
        self.patcher = patcher
        self.config = config

    def include(self, name: str) -> None:
        """The function `include` adds a given patch to a list of patches.

        Parameters
        ----------
        name : str
            The `name` parameter is a string that represents the name of the patch to be included.
        """
        self._PATCHES.extend(["-i", name])

    def exclude(self, name: str) -> None:
        """The `exclude` function adds a given patch to the list of excluded
        patches.

        Parameters
        ----------
        name : str
            The `name` parameter is a string that represents the name of the patch to be excluded.
        """
        self._PATCHES.extend(["-e", name])
        self._EXCLUDED.append(name)

    def get_excluded_patches(self) -> List[str]:
        """The function `get_excluded_patches` is a getter method that returns
        a list of excluded patches.

        Returns
        -------
            The method is returning a list of excluded patches.
        """
        return self._EXCLUDED

    def get_all_patches(self) -> List[str]:
        """The function "get_all_patches" is a getter method that returns a
        list of all patches.

        Returns
        -------
            The method is returning a list of all patches.
        """
        return self._PATCHES

    def invert_patch(self, name: str) -> bool:
        """The function `invert_patch` takes a name as input, it toggles the
        status of the patch and returns True, otherwise it returns False.

        Parameters
        ----------
        name : str
            The `name` parameter is a string that represents the name of a patch.

        Returns
        -------
            a boolean value. It returns True if the patch name is found in the list of patches and
        successfully inverted, and False if the patch name is not found in the list.
        """
        try:
            name = name.lower().replace(" ", "-")
            patch_index = self._PATCHES.index(name)
            indices = [i for i in range(len(self._PATCHES)) if self._PATCHES[i] == name]
            for patch_index in indices:
                if self._PATCHES[patch_index - 1] == "-e":
                    self._PATCHES[patch_index - 1] = "-i"
                else:
                    self._PATCHES[patch_index - 1] = "-e"
            return True
        except ValueError:
            return False

    def exclude_all_patches(self) -> None:
        """The function `exclude_all_patches` replaces all occurrences of "-i"
        with "-e" in the list `self._PATCHES`.

        Hence exclude all patches
        """
        for idx, item in enumerate(self._PATCHES):
            if item == "-i":
                self._PATCHES[idx] = "-e"

    # noinspection IncorrectFormatting
    def patch_app(
        self,
        app: APP,
    ) -> None:
        """The function `patch_app` is used to patch an app using the Revanced
        CLI tool.

        Parameters
        ----------
        app : APP
            The `app` parameter is an instance of the `APP` class. It represents an application that needs
        to be patched.
        """
        args = [
            self.CLI_JAR,
            app.resource["cli"],
            self.APK_ARG,
            app.download_file_name,
            self.PATCHES_ARG,
            app.resource["patches"],
            self.INTEGRATIONS_ARG,
            app.resource["integrations"],
            self.OUTPUT_ARG,
            app.get_output_file_name(),
            self.KEYSTORE_ARG,
            app.keystore_name,
            self.OPTIONS_ARG,
            "options.json",
        ]
        if app.experiment:
            logger.debug("Using experimental features")
            args.append("--experimental")
        args[1::2] = map(self.config.temp_folder.joinpath, args[1::2])
        if self.config.ci_test:
            self.exclude_all_patches()
        if self._PATCHES:
            args.extend(self._PATCHES)
        if app.app_name in self.config.rip_libs_apps:
            excluded = set(possible_archs) - set(app.archs_to_build)
            for arch in excluded:
                args.extend(("--rip-lib", arch))
        start = perf_counter()
        logger.debug(
            f"Sending request to revanced cli for building with args java {args}"
        )
        process = Popen(["java", *args], stdout=PIPE)
        output = process.stdout
        if not output:
            raise PatchingFailed("Failed to send request for patching.")
        for line in output:
            logger.debug(line.decode(encoding='cp949'), flush=True, end="")
        process.wait()
        logger.info(
            f"Patching completed for app {app} in {perf_counter() - start:.2f} seconds."
        )
