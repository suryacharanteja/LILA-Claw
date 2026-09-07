# M0 license inventory review

The Python distribution metadata/license files and npm lock license metadata are
captured in python-licenses.json, dependency-licenses/ and npm-licenses.json.
Original project LICENSE and NOTICE are retained; no legacy implementation code
was copied into the new foundation.

This is a development/build inventory, not final bundled-distribution clearance.
The environment includes code generation, testing and packaging tools that need
not ship in the application. PyInstaller's GPL exception and LGPL-bearing document
dependencies require their applicable notices/conditions in the M7 distribution.
LangSmith metadata declares MIT but its installed distribution did not include a
license text in the scanned dist-info directory; retrieve its authoritative notice
and determine whether it ships before release. Missing metadata fields for other
packages are supplemented by captured license text and classifiers.

M7 must derive a bundle-specific notice inventory, including Node build tools,
native SQLCipher components, fonts and installer runtime. No stable release is
authorized by this inventory.

