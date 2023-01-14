# -*- coding: utf-8 -*-

"""Module for finding the corresponding package from Contents file"""

import logging
import subprocess

from typing import List, Set
from pathlib import Path

from .magic import FileInfo
from .utils import generate_pattern
from .readelf import SharedLibrary, AggregatedLibraries

DPKG_GET_ARCHITECTURE: List[str] = [
    '/usr/bin/dpkg-architecture', '-q', 'DEB_BUILD_ARCH']
DPKG_CONTENTS_PATH: Path = Path('/var/lib/apt/lists/')
GREP_REGEX: List[str] = ['/usr/bin/grep', '--color=never', '-E']
RG_REGEX: List[str] = ['/usr/bin/rg', '--color=never', '-e']


class ContentsEntry(object):
    _path: Path
    _library: SharedLibrary
    _packages: List[str]

    def __init__(self, line: str):
        split_at = None
        # Find the rightmost whitespace character
        for i in range(len(line) - 1, 0, -1):
            if line[i] in [' ', '\t']:
                split_at = i
                break
        # TODO: Better error handling
        path = line[:split_at].strip()
        # Remove the './' prefix
        if path.startswith('.'):
            path = path[1:]
        if path.startswith('/'):
            path = path[1:]
        self._path = Path(path)
        # Construct a library object
        self._library = SharedLibrary(self._path.name)
        # Generate packages
        packages = line[split_at:].strip().split(',')
        # Python slice magic to extract package name
        self._packages = list(map(
            lambda name: name.rsplit('/', maxsplit=1)[-1:][0], packages))

    def __repr__(self) -> str:
        return "ContentsEntry('{}   {}')".format(
            self._path, ','.join(self._packages))

    def get_path(self) -> Path:
        return self._path

    def get_library(self) -> SharedLibrary:
        return self._library

    def get_packages(self) -> List[str]:
        return self._packages


class Contents(object):
    _libs: AggregatedLibraries
    _first_pass: bytes
    _prog: List[str]

    def __init__(self, libs: AggregatedLibraries):
        rg_prog = RG_REGEX[0]
        grep_prog = GREP_REGEX[0]
        if FileInfo.is_elf(Path(rg_prog)):
            self._prog = RG_REGEX
        elif FileInfo.is_elf(Path(grep_prog)):
            self._prog = GREP_REGEX
        else:
            logging.error(f'{rg_prog} and {grep_prog} not found, exiting ...')
            exit(1)
        logging.debug(f'Using {self._prog} as grep implementation')
        self._libs = libs
        pattern = self._libs.get_grep_filter()
        self._first_pass = bytes()
        for content_list in self._find_lists():
            self._first_pass += \
                self._run_grep_first_pass(pattern, content_list, self._prog)

    @staticmethod
    def _generate_grep_pattern(packages: List[SharedLibrary]) -> str:
        segments = map(
            lambda lib: "({} )".format(
                lib.get_full_name().replace('.', '\\.')),
            packages)
        return '|'.join(segments)

    @staticmethod
    def _get_architecture() -> str:
        prog = DPKG_GET_ARCHITECTURE[0]
        if not Path(prog).exists():  # This one is a script
            logging.error(f'{prog} not found, exiting ...')
            exit(1)
        return subprocess.run(
            DPKG_GET_ARCHITECTURE, check=True, capture_output=True)\
            .stdout.decode('utf-8', 'ignore').strip()

    @staticmethod
    def _find_lists() -> List[Path]:
        if not (DPKG_CONTENTS_PATH.exists() and DPKG_CONTENTS_PATH.is_dir()):
            logging.error('Unable to find DPKG contents files, exiting ...')
        return list(DPKG_CONTENTS_PATH.rglob(
            "*_Contents-{}.*".format(Contents._get_architecture())))

    @staticmethod
    def _run_grep_first_pass(
        pattern: str,
        path: Path,
        prog: List[str]
    ) -> bytes:
        algorithm = path.suffix[1:]
        cat_cmd = Path(f'/usr/bin/{algorithm}cat')
        if not FileInfo.is_elf(cat_cmd):
            logging.error(f'{cat_cmd} not found, exiting ...')
            exit(1)
        cat_args = [str(cat_cmd), str(path)]
        cat = subprocess.Popen(
            cat_args, stdout=subprocess.PIPE)
        grep_args = prog + [pattern]
        grep = subprocess.Popen(
            grep_args,
            stdin=cat.stdout,
            stdout=subprocess.PIPE)
        # Pylance does not recognize the following line
        # LMAO this is in subprocess's documentation
        cat.stdout.close()  # type: ignore
        return grep.communicate()[0]

    @staticmethod
    def _run_grep(
        soname: str,
        contents: bytes,
        prog: List[str]
    ) -> List[ContentsEntry]:
        grep_args = prog + [generate_pattern(soname)]
        grep = subprocess.Popen(
            grep_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        result = grep.communicate(input=contents)[0].decode('utf-8')
        return list(map(lambda line: ContentsEntry(line), result.splitlines()))

    def run_grep(self, soname: str) -> List[ContentsEntry]:
        return self._run_grep(soname, self._first_pass, self._prog)


def get_packages(entries: List[ContentsEntry]) -> Set[str]:
    ret: Set[str] = set()
    for entry in entries:
        packages = set(entry.get_packages())
        ret = ret.union(packages)
    return ret
