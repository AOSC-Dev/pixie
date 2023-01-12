# -*- coding: utf-8 -*-

"""
Readelf binding
"""

import logging
import subprocess

from re import Pattern, MULTILINE, compile
from typing import List, Optional, Any, Dict, TypeVar, Set
from pathlib import Path

from .magic import is_elf
from .utils import generate_pattern

# Max length of paths
MAX_PATH_LEN: int = 4096
# Max length of filenames
MAX_FILENAME_LEN: int = 255

# Match both rpath and sonames
READELF_D_REGEX: Pattern[str] = compile(r"0x[0-9a-fA-F]+[ \t]+((\(((RPATH)|(RUNPATH))\)[ \t]+Library ((rpath)|(runpath)):[ \t]*\[(?P<rpath>.*)\]$)|(\(NEEDED\)[ \t]+Shared library:[ \t]+\[(?P<library>.*)\]$))", MULTILINE)  # noqa: E501

# Match sonames in dumped strings
READELF_P_REGEX: Pattern[str] = compile(r"(?P<soname>lib[a-zA-Z0-9-_]+.so(.[0-9]+)*)", MULTILINE)  # noqa: E501

# Match dlopen in readelf -s
READELF_S_REGEX: Pattern[str] = compile(r"UND[ \t]+dlopen", MULTILINE)


class ReadELFException(Exception):
    """Raised when readelf give no output or the return code is not 0"""
    pass


class SharedLibrary(object):
    _soname: str
    _sover: List[int]

    def __init__(self, name: str):
        segments = name.strip().split('.so.', maxsplit=1)
        # Get soname
        if segments[0].endswith('.so'):
            self._soname = segments[0][:-3]
        else:
            self._soname = segments[0]
        # Parse sover
        if len(segments) == 2:
            sover = segments[1].split('.')
            try:
                self._sover = list(map(lambda ver: int(ver), sover))
            except ValueError as e:
                logging.debug(f'Failed to parse the sover of {name}: {e}')
                self._sover = []
        else:
            self._sover = []

    def get_sover_string(self) -> str:
        return '.'.join(map(lambda ver: str(ver), self._sover))

    def get_soname(self) -> str:
        return self._soname

    def get_full_name(self) -> str:
        sover_str = ''
        if len(self._sover) > 0:
            sover_str = '.' + self.get_sover_string()
        return "{}.so{}".format(self.get_soname(), sover_str)

    def __repr__(self) -> str:
        return "SharedLibrary({})".format(self.get_full_name())

    def __str__(self) -> str:
        return self.get_soname()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SharedLibrary):
            return False
        return other._soname == self._soname

    def is_external(self, rpath: List[Path]) -> bool:
        name = self.get_full_name()
        return not any(map(lambda p: (p / name).exists(), rpath))


class SharedLibraryOutput(object):
    _libraries: List[SharedLibrary]
    _origin_path: Path
    _rpath: List[Path]

    def __init__(
        self,
        origin_path: Path,
        rpath: Optional[List[Path]] = None,
        libraries: Optional[List[SharedLibrary]] = []
    ):
        self._libraries = libraries or []
        self._origin_path = origin_path
        self._rpath = rpath or [self._origin_path]  # Defaults to $ORIGIN

    def __repr__(self) -> str:
        return "SharedLibraryOutput({}, rpath={}, libraries={})".format(
            self._origin_path,
            self._rpath,
            repr(self._libraries)
        )

    def parse_rpath(self, input: str) -> List[Path]:
        replaced = input.replace('$ORIGIN', str(self._origin_path))
        return list(map(lambda p: Path(p), replaced.split(':')))

    def parse_bytes_dynamic(self, output: Optional[bytes]):
        if output is None:
            return
        matches = READELF_D_REGEX.finditer(output.decode('utf-8', 'ignore'))
        for match in matches:
            groups = match.groupdict()
            # Update rpath
            rpath = groups.get('rpath')
            if isinstance(rpath, str) and (len(rpath) < MAX_PATH_LEN):
                self._rpath += self.parse_rpath(rpath)
            # Update libraries
            library = groups.get('library')
            if isinstance(library, str) and (len(library) < MAX_FILENAME_LEN):
                self._libraries.append(SharedLibrary(library))

    def parse_bytes_string_dump(self, output: Optional[bytes]):
        if output is None:
            return
        matches = READELF_P_REGEX.finditer(output.decode('utf-8', 'ignore'))
        for match in matches:
            lib = match.groupdict().get('soname')
            if isinstance(lib, str) and (len(lib) < MAX_FILENAME_LEN):
                self._libraries.append(SharedLibrary(lib))

    def get_libraries(self) -> List[SharedLibrary]:
        return self._libraries

    def get_external_libraries(self) -> List[SharedLibrary]:
        return list(filter(
            lambda lib: lib.is_external(self._rpath), self._libraries))


class ReadELF(object):
    DEFAULT_ARGS: List[str] = ['/usr/bin/readelf']

    @staticmethod
    def check_program() -> bool:
        prog = ReadELF.DEFAULT_ARGS[0]
        return is_elf(Path(prog))

    @staticmethod
    def _run_command(args: List[str]) -> Optional[bytes]:
        try:
            output = subprocess.run(
                ReadELF.DEFAULT_ARGS + args, capture_output=True, check=True)
            return output.stdout
        except subprocess.SubprocessError:
            raise ReadELFException('`readelf` process exited with error')

    @staticmethod
    def read_dynamic(file: Path) -> SharedLibraryOutput:
        ret = SharedLibraryOutput(file.parent)
        output = ReadELF._run_command(['-d', str(file)])
        ret.parse_bytes_dynamic(output)
        return ret

    @staticmethod
    def find_so(file: Path, section: str) -> SharedLibraryOutput:
        ret = SharedLibraryOutput(file.parent)
        filename = str(file)
        # Makesure the file contains dlopen in its symbol table
        syms = ReadELF._run_command(['-s', filename])
        if syms is None:
            logging.debug(
                f'Failed to get symbols from {filename}, ignoring ...')
            return ret
        if READELF_S_REGEX.search(syms.decode('utf-8', 'ignore')) is None:
            logging.debug(
                f'{filename} does not contain dlopen in its symbols ' +
                'ignoring ...')
            return ret
        # Read ELF
        output = ReadELF._run_command(['-p', section, filename])
        ret.parse_bytes_string_dump(output)
        return ret


TAggregatedLibraries = TypeVar(
    'TAggregatedLibraries', bound='AggregatedLibraries')


class AggregatedLibraries(object):
    _libs: Dict[str, Set[str]]

    def __init__(self, libs: List[SharedLibrary]):
        self._libs = dict()
        for lib in libs:
            soname = lib.get_soname()
            sovers: Set[str] = self._libs.get(soname) or set()
            sover = lib.get_sover_string()
            if sover:
                sovers.add(sover)
            self._libs[soname] = sovers

    def __str__(self) -> str:
        ret: List[str] = []
        for (k, v) in self._libs.items():
            if len(v) > 0:
                v_list = list(v)
                v_list.sort()
                vers = ' ({})'.format(' or '.join(v_list))
            else:
                vers = ''
            ret.append('{}.so{}'.format(k, vers))
        return ', '.join(ret)

    def __len__(self) -> int:
        return len(self._libs)

    def __add__(
        self: TAggregatedLibraries,
        other: Any
    ) -> TAggregatedLibraries:
        if not isinstance(other, AggregatedLibraries):
            return self
        for (k, v) in other._libs.items():
            sovers = self._libs.get(k) or set()
            self._libs[k] = sovers.union(v)
        return self

    def get_inner(self) -> Dict[str, Set[str]]:
        return self._libs

    def get_sonames(self) -> Set[str]:
        return set(self._libs.keys())

    def get_grep_filter(self) -> str:
        ret: List[str] = []
        for soname in self._libs.keys():
            ret.append(f'({generate_pattern(soname)})')
        return '|'.join(ret)
