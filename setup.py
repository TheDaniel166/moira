from __future__ import annotations

import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = ".") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = str(Path(sourcedir).resolve())


class CMakeBuild(build_ext):
    def build_extension(self, ext: Extension) -> None:
        if not isinstance(ext, CMakeExtension):
            super().build_extension(ext)
            return

        cmake_exe = shutil.which("cmake")
        if cmake_exe is None:
            raise RuntimeError("CMake is required to build moira._moira_native")

        try:
            import pybind11
        except ImportError as exc:
            raise RuntimeError("pybind11 is required to build moira._moira_native") from exc

        ext_fullpath = Path(self.get_ext_fullpath(ext.name)).resolve()
        source_root = Path(ext.sourcedir).resolve()
        provenance_module = runpy.run_path(
            str(source_root / "moira" / "_native_build_provenance.py")
        )
        build_manifest = provenance_module["native_build_input_manifest"](
            source_root
        )
        build_temp = Path(self.build_temp).resolve() / ext.name.replace(".", "_")
        source_snapshot = build_temp.parent / f"{build_temp.name}_source_snapshot"
        shutil.rmtree(build_temp, ignore_errors=True)
        shutil.rmtree(source_snapshot, ignore_errors=True)
        build_temp.mkdir(parents=True, exist_ok=True)
        provenance_module["stage_native_build_snapshot"](
            source_root,
            source_snapshot,
            build_manifest,
        )
        build_lib = Path(self.build_lib).resolve()
        build_lib.mkdir(parents=True, exist_ok=True)

        config = "Debug" if self.debug else "Release"
        pybind11_dir = Path(pybind11.get_cmake_dir()).resolve()

        configure_args = [
            f"-S{source_snapshot}",
            f"-B{build_temp}",
            f"-DCMAKE_BUILD_TYPE={config}",
            f"-DPython3_EXECUTABLE={sys.executable}",
            f"-Dpybind11_DIR={pybind11_dir}",
            f"-DMOIRA_EXTENSION_FULL_OUTPUT_PATH={ext_fullpath}",
            "-DMOIRA_NATIVE_BUILD_INPUT_MANIFEST_SHA256="
            f"{build_manifest['sha256']}",
        ]
        build_args = ["--build", str(build_temp), "--config", config]
        install_args = ["--install", str(build_temp), "--config", config, "--prefix", str(build_lib)]

        parallel = os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL")
        if parallel:
            build_args.extend(["--parallel", parallel])
        elif self.parallel:
            build_args.extend(["--parallel", str(self.parallel)])

        subprocess.run([cmake_exe, *configure_args], check=True)
        subprocess.run([cmake_exe, *build_args], check=True)
        subprocess.run([cmake_exe, *install_args], check=True)
        final_snapshot_manifest = provenance_module[
            "native_build_input_manifest"
        ](source_snapshot)
        if final_snapshot_manifest != build_manifest:
            raise RuntimeError(
                "native build snapshot changed while CMake was compiling it"
            )

        package_dir = ext_fullpath.parent
        for pattern in ("_moira_native*.exp", "_moira_native*.lib"):
            for artifact in package_dir.glob(pattern):
                artifact.unlink()


setup(
    ext_modules=[CMakeExtension("moira._moira_native")],
    cmdclass={"build_ext": CMakeBuild},
)
