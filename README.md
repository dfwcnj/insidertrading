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

This package used to use stock price history but the cost has become too
great. It now just reports insiders sorted by dollar amount as reported
in NONDERIV_TRANS


THIS DOES NOT CLAIM THAT ANY OF THESE TRANSACTIONS ARE ILLEGAL.

If you do not provide a --yq argument, the command determines the last
quarter from the current date and uses that

if you do not provide an --insiderdb argument, the sqlite3 database is
created in RAM.

## Usage

usage: edgarinsidertrading [-h] [--yq YQ] [--sdate SDATE] [--edate EDATE]<br>
                           [--insiderdb INSIDERDB]<br>
                           [--directory DIRECTORY]<br>
                           [--file FILE]<br>
                           [--verbose]<br>

report possibly illegal insider trading<br>

options:<br>
  -h, --help            show this help message and exit<br>
  --yq YQ               year quarter in form YYYYQ[1-4]<br>
  --sdate SDATE         first day of trades to check<br>
  --edate EDATE         last day of trades to check<br>
  --insiderdb INSIDERDB<br>
             full path to the sqlite3 database - default in memory<br>
  --directory DIRECTORY<br>
             directory to store the output<br>
  --file FILE           csv file to store the output - default stdout<br>
  --verbose             reveal some of the process<br>

