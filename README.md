# insidertrading

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install insidertrading
```

## License

`insidertrading` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Description

This package chooses the largest dollar transactions in the SEC form345
file and reports transactions where the stock price rose, in case of an
acquisition, or fell, in case of a disposal, over a certain percentage
dugine the following week.

THIS DOES NOT CLAIM THAT ANY OF THESE TRANSACTIONS ARE ILLEGAL.

It merely reports that the stock moved by some threshold after the
transaction. It could be because of coincidence, because the stock is
unusually volatile, or some other innocuous reason.

If you do not provide a --yq argument, the command determins the last
quarter from the current date and uses that

if you do not provide an --insiderdb argument, the sqlite3 database is
created in the current directory

## Usage

usage: edgarinsidertrading [-h] [--directory DIRECTORY]
                           [--insiderdb INSIDERDB] [--yq YQ]

report possibly illegal insider trading

options:
  -h, --help            show this help message and exit
  --directory DIRECTORY
                        directory to store the output
  --insiderdb INSIDERDB
                        full path to the sqlite3 database
  --yq YQ               year quarter in form YYYYQ[1-4]
