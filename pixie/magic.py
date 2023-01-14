# -*- coding: utf-8 -*-

import subprocess

from os import walk
from enum import Enum
from typing import Iterable, Optional, List, Dict
from pathlib import Path

ELF_MAGIC: bytes = b'\x7fELF'

CHARSETS: Dict[str, Optional[str]] = {
    'us-ascii': 'utf-8',
    'binary': None,
}


class FileException(Exception):
    """Raised when file give no output or the return code is not 0"""
    pass


class FileType(Enum):
    ELF = 0
    PYTHON = 1
    PERL = 2
    ELSE = 99


FILE_TYPES: Dict[str, FileType] = {
    'text/x-script.python': FileType.PYTHON,
    'text/x-perl': FileType.PERL,
}


class FileInfo(object):
    DEFAULT_ARGS: List[str] = ['file', '-ib']
    _type: FileType
    _path: Path
    _charset: Optional[str]

    @staticmethod
    def _get_mime(file: Path) -> str:
        try:
            output = subprocess.run(
                FileInfo.DEFAULT_ARGS + [str(file)],
                capture_output=True,
                check=True)
            return output.stdout.decode('utf-8', 'ignore')
        except subprocess.SubprocessError:
            raise FileException('`file` process exited with error')

    @staticmethod
    def is_elf(file: Path):
        magic: bytes = bytes()
        with open(file, 'rb') as f:
            magic = f.read(4)
        return magic == ELF_MAGIC

    def __init__(self, path: Path):
        self._path = path
        if self.is_elf(path):
            self._type = FileType.ELF
            self._charset = None
        mime = self._get_mime(path)
        mime_segments = mime.split('; ')
        for segment in mime_segments:
            if segment.startswith('charset='):
                charset_text = segment[7:]
                self._charset = CHARSETS.get(charset_text) or charset_text
                continue
            self._type = FILE_TYPES.get(segment) or FileType.ELSE


def find_elfs(path: Path) -> Iterable[Path]:
    if path.is_file():
        if FileInfo.is_elf(path):
            yield path
        return None
    for (root, _, files) in walk(path):
        dir = Path(root)
        for file in files:
            path = dir / file
            try:
                if FileInfo.is_elf(path):
                    yield path
            except (IOError, PermissionError):
                continue
