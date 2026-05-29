import argparse
import subprocess
import os
import sys
import json
import magic
from datetime import datetime
# from PIL import Image
import exifread
from collections import namedtuple

from .batch import Batch, BatchFull
from fparts import batch

def get_args():
    parser = argparse.ArgumentParser(description="File parting/grouping/renaming tool (like fpart): all you need for grouping and sorting files")
    parser.add_argument('paths', nargs='+', help='Paths to files or directories to process')
    parser.add_argument('-b', '--batch-size', type=str, default="100", help='Number of files per group (default: 100), or give a size in bytes (10M)')    
    parser.add_argument('-s', '--sort-by', choices=['name', 'size', 'date'], default='name', help='Sort files by name, size, or modification time (default: name)')
    parser.add_argument('-d', '--datesource', type=str, default='mnf', 
                        help='source of date/time m: media info (e.g. for mp4 creation time), n: file name (e.g. YYYYMMDD), f: file modification time (default: mnf)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process input directories recursively')
    parser.add_argument('-R', '--reverse', action='store_true', help='Reverse the sorting order')

    g = parser.add_argument_group('Output options')
    g.add_argument('--move', action='store_true', help='Move files to group directories instead of copying')
    g.add_argument('-o', '--output', default='batch-', help='Output directory for the groups (default: output-NNN). NNN will be replaced with group number')
    g.add_argument('-n', '--name', default=None, help='If given, rename files in groups to a common format (use this prefix, index, same extension, e.g. -n image-)')
    g.add_argument('-c', '--continuous', action='store_true', help='Use continuous numbering across groups when renaming files (with -n)')
    g.add_argument('--dry', '--dry-run', action='store_true', help='Show what would be done without actually moving/copying files')
    g.add_argument('-z', '--zeroes', type=int, default=3, help='Number of leading zeros for batch numbers (default: 3)')

    return parser.parse_args()


def read_filelist(paths, recursive):

    all_files = []
    for path in paths:
        if os.path.isfile(path):
            all_files.append(path)

        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    all_files.append(os.path.join(root, file))
                if not recursive:
                    break
        else:
            print(f"Warning: {path} is not a valid file or directory and will be skipped")
    return all_files


def get_mp4_created(file):    
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format_tags=creation_time', '-of', 'json', file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Warning: ffprobe failed for {file}: {result.stderr.strip()}")
            return None

        data = json.loads(result.stdout)
        creation_time = data.get('format', {}).get('tags', {}).get('creation_time')
        return datetime.fromisoformat(creation_time) if creation_time else None
    except Exception as e:
        print(f"Warning: Could not get creation time for {file}: {e}")
        return None

def get_exif_date_exifread(file):
    with open(file, 'rb') as f:
        tags = exifread.process_file(f)
        date_tag = tags.get('EXIF DateTimeOriginal')
        if date_tag:
            print(f"EXIF date for {file}: {date_tag}")
            return datetime.strptime(str(date_tag), "%Y:%m:%d %H:%M:%S")

def file_date(file, datesource):
    for src in datesource:        
        if src == 'm':
            media_type = magic.from_file(file, mime=True)
            
            if media_type == "video/mp4":
                created = get_mp4_created(file)
                if created:
                    return created
            
            if media_type.startswith("image/"):
                created = get_exif_date_exifread(file)
                if created:
                    return created

        elif src == 'n':
            # Try to extract date from filename (e.g. YYYYMMDD)
            basename = os.path.basename(file)
            date_str = ''.join(filter(str.isdigit, basename))
            if len(date_str) >= 8:
                created = datetime.strptime(date_str[:8], "%Y%m%d")
                return created
        elif src == 'f':
            # get datetime from file modification time
            return datetime.fromtimestamp(os.path.getmtime(file))
        else:
            raise ValueError(f"Invalid datesource: {datesource}")

def sort_files(all_files, datesource='mnf', sort_by='name', reverse=False):

    files_metrics = []

    FileInfo = namedtuple("FileInfo", ["fullpath", "relpath", "basename", "size", "mtime", "media_type", "metric"])

    for file in all_files:
        try:
            stat = os.stat(file)
            size = stat.st_size
            mtime = stat.st_mtime
            media_type = magic.from_file(file, mime=True)
          
            if sort_by == 'date':
                metric = file_date(file, datesource)
            elif sort_by == 'size':
                metric = size
            else:
                metric = os.path.basename(file)
            
            files_metrics.append(FileInfo(file, os.path.relpath(file), os.path.basename(file), size, mtime, media_type, metric))
        except Exception as e:
            print(f"Warning: Could not access file {file}: {e}")

    print(f"sort. rev: {reverse}, by: {sort_by}, date source: {datesource}")
    return sorted(files_metrics, key=lambda x: x.metric, reverse=reverse)



def process_file(file_info: tuple, output: str, zeroes: int, move:bool, rename_pattern=None, batch_index=1, file_index=1, dry_run=False):

    output_dir = f'{output}{batch_index:0{zeroes}d}'
    os.makedirs(output_dir, exist_ok=True)

    if rename_pattern:
        _, ext = os.path.splitext(file_info.basename)
        new_name = f'{rename_pattern}{file_index:0{zeroes}d}{ext}'
    else:
        new_name = file_info.basename
    src = file_info.fullpath
    dst = os.path.join(output_dir, new_name)    
    if dry_run:
        print(f"Would {'move' if move else 'copy'} {src} to {dst}")
    else:
        if move:
            print(f"Moving {src} to {dst}")
            os.rename(src, dst)
        else:
            print(f"Copying {src} to {dst}")
            subprocess.run(['cp', src, dst], check=True)



def main():
    args = get_args()    
    
    files = read_filelist(args.paths, args.recursive)
    files_metrics = sort_files(files, args.datesource, args.sort_by, args.reverse)



    batch = Batch(args.batch_size)
    for fm in files_metrics:
        try:
            batch.add_file(fm)
        except BatchFull:
            print(f"File {fm.relpath} could not be added to batch {batch.index}")
            for idx, f in enumerate(batch):                
                process_file(f, args.output, args.zeroes, args.move, args.name, batch_index=batch.index, file_index=idx+1, dry_run=args.dry)

            batch = Batch(args.batch_size)
            batch.add_file(fm)

    # process remaining files in the last batch
    
    for idx, f in enumerate(batch):        
        process_file(f, args.output, args.zeroes, args.move, args.name, batch_index=batch.index, file_index=idx+1, dry_run=args.dry)            

if __name__ == '__main__':
    main()