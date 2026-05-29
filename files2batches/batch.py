batch_index = 0

class BatchFull(Exception):
    # raised when cannot add a file to a batch because it would exceed the batch size limit
    pass

class Batch:
    index: int # sequential index of the batch
    size: int # either number of files or total size in bytes, depending on how it was initialized
    limit_in_bytes: bool # whether the size is a byte limit (True) or a file count (False)
    
    def __init__(self, size: str):
        global batch_index
        """ size is either number of files (e.g. 100) or size in bytes OR human-readable size (e.g. 10M, 10MB, 10GB) """
        self.index = batch_index
        batch_index += 1
        self.files = []
        self.current_size = 0
    
        """  Parse size string: if it ends with K/M/G or KB/MB/GB, multiply by 1024/1024/1024, otherwise treat as number of files """
        size = size.upper()
        self.limit_in_bytes = any(size.endswith(suffix) for suffix in ['KB', 'MB', 'GB', 'K', 'M', 'G'])
        if size.endswith('KB'):
            self.size = int(float(size[:-2]) * 1024)
        elif size.endswith('MB'):
            self.size = int(float(size[:-2]) * 1024**2)
        elif size.endswith('GB'):
            self.size = int(float(size[:-2]) * 1024**3)
        elif size.endswith('K'):
            self.size = int(float(size[:-1]) * 1024)
        elif size.endswith('M'):
            self.size = int(float(size[:-1]) * 1024**2)
        elif size.endswith('G'):
            self.size = int(float(size[:-1]) * 1024**3)
        else:
            self.size = int(size)
        

    def add_file(self, file_info):
        """ file_info is a namedtuple with at least 'size' attribute """        
        if self.limit_in_bytes:            
            if self.current_size + file_info.size > self.size:
                raise BatchFull(f"Cannot add file {file_info.relpath} (size {file_info.size} bytes) to batch {self.index} because it would exceed the batch size limit of {self.size} bytes")
            self.current_size += file_info.size

        else:
            if len(self.files) >= self.size:
                raise BatchFull(f"Cannot add file {file_info.relpath} to batch {self.index} because it already has the maximum number of files ({self.size})")
            self.current_size += 1
        
        self.files.append(file_info)

    def __iter__(self):
        return iter(self.files)

    def __repr__(self):
        return f"Batch {self.index} (size: {self.size}, files: {len(self.files)})"