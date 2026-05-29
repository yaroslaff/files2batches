# files2batches
Group files into sorted batches (using filenames, mtime or metadata). 

## Installation
~~~
pipx install git+https://github.com/yaroslaff/files2batches.git
~~~

## Usage examples
~~~
# very basic, group files (recursively) into directores batch-NNN, 100 files in each
# default sort order (datetime from metadata if available, otherwise from guessed from filename, and mtime)
files2batches -r /tmp/test/
~~~

## Options
~~~
usage: files2batches [-h] [-b BATCH_SIZE] [-s {name,size,date}] [-d DATESOURCE] [-r] [-R] [--move] [-o OUTPUT] [-n NAME] [-c] [--dry] [-z ZEROES] paths [paths ...]

File parting/grouping/renaming tool (like fpart): all you need for grouping and sorting files

positional arguments:
  paths                 Paths to files or directories to process

options:
  -h, --help            show this help message and exit
  -b, --batch-size BATCH_SIZE
                        Number of files per group (default: 100), or give a size in bytes (10M)
  -s, --sort-by {name,size,date}
                        Sort files by name, size, or modification time (default: name)
  -d, --datesource DATESOURCE
                        source of date/time m: media info (e.g. for mp4 creation time), n: file name (e.g. YYYYMMDD), f: file modification time (default: mnf)
  -r, --recursive       Process input directories recursively
  -R, --reverse         Reverse the sorting order

Output options:
  --move                Move files to group directories instead of copying
  -o, --output OUTPUT   Output directory for the groups (default: output-NNN). NNN will be replaced with group number
  -n, --name NAME       If given, rename files in groups to a common format (use this prefix, index, same extension, e.g. -n image-)
  -c, --continuous      Use continuous numbering across groups when renaming files (with -n)
  --dry, --dry-run      Show what would be done without actually moving/copying files
  -z, --zeroes ZEROES   Number of leading zeros for batch numbers (default: 3)
  ~~~