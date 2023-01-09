pixie
=====

Dependency scanner of ELF executables for DPKG-based Linux distributions.

Requirements
------------

 - For fetching sonames:
   - `readelf` from `binutils`
 - For generating PKGDEP:
   - `dpkg-architecture` from `dpkg`
   - `rg` or `grep`

Usage
-----

```
usage: pscan [-h] [-l] [-s] [-v] [-i] path

pixie(version 0.1.20230123) - Dependency scanner for ELF executables

positional arguments:
  path               Path to the target, could be a directory or a file

options:
  -h, --help         show this help message and exit
  -l, --linked-only  Show linked dependencies only
  -s, --soname-only  Print sonames only, defaults to generating PKGDEP
  -v, --verbose      Verbosity of the output
  -i, --interactive  Interactively choose when multiple packages offer same
                     library
```
