
from typing import List, Set


class Process:
    def __init__(self, pid, name):
        self.pid = pid
        self.name = name

    def get_uuid(self):
        return f"{self.name}-{self.pid}"

    def __str__(self):
        return f'Process(pid={self.pid}, name={self.name})'
    
    def __repr__(self):
        return str(self)
    

class FileType:
    FIFO = 0
    CHAR_DEVICE = 1
    DIRECTORY = 2
    BLOCK_DEVICE = 3
    REGULAR_FILE = 4
    SYMLINK = 5
    SOCKET = 6
    UNKNOWN = 7

    S_IFIFO = 0o0010000   # FIFO
    S_IFCHR = 0o0020000   # character device
    S_IFDIR = 0o0040000   # directory
    S_IFBLK = 0o0060000   # block device
    S_IFREG = 0o0100000   # regular file
    S_IFLNK = 0o0120000   # symlink
    S_IFSOCK = 0o0140000  # socket

    translation_table = {
        S_IFIFO: FIFO,
        S_IFCHR: CHAR_DEVICE,
        S_IFDIR: DIRECTORY,
        S_IFBLK: BLOCK_DEVICE,
        S_IFREG: REGULAR_FILE,
        S_IFLNK: SYMLINK,
        S_IFSOCK: SOCKET
    }

    @staticmethod
    def from_octal(octal: int):
        return FileType.translation_table.get(octal, FileType.UNKNOWN)


    def __str__(self) -> str:
        if self == FileType.FIFO:
            return "FIFO"
        elif self == FileType.CHAR_DEVICE:
            return "CHAR DEVICE"
        elif self == FileType.DIRECTORY:
            return "DIRECTORY"
        elif self == FileType.BLOCK_DEVICE:
            return "BLOCK DEVICE"
        elif self == FileType.REGULAR_FILE:
            return "REGULAR FILE"
        elif self == FileType.SYMLINK:
            return "SYMLINK"
        elif self == FileType.SOCKET:
            return "SOCKET"
        else:
            return "UNKNOWN"

    def __repr__(self):
        return str(self)


class CommunicationChannel:
    def __init__(self, name, type, direction):
        self.name: str = name
        self.type: FileType = type
        self.direction: CommunicationDirection = direction

    def __str__(self) -> str:
        return f'CommunicationChannel(name={self.name}, type={self.type}, direction={self.direction})'

    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        return self.name == other.name and self.type == other.type and self.direction == other.direction


class CommunicationDirection:
    READ = 0
    WRITE = 1

    def __str__(self) -> str:
        if self == CommunicationDirection.READ:
            return "READ"
        elif self == CommunicationDirection.WRITE:
            return "WRITE"
        else:
            return "UNKNOWN"
        
    def __repr__(self):
        return str(self)


class CommunicationInfo:
    def __init__(self, timestamp, channel, fd, direction, size, content):
        self.timestamp = timestamp
        self.channel = channel
        self.fd = fd
        self.direction = direction
        self.size = size
        self.content = content
    
    def __str__(self) -> str:
        return f'CommunicationInfo(timestamp={self.timestamp}, channel={self.channel}, fd={self.fd}, direction={self.direction}, size={self.size}, content={self.content})'

    def __repr__(self):
        return str(self)


class FileRights:
    
    def __init__(self, uid, uread, uwrite, uexec, gid, gread, gwrite, gexec, oread, owrite, oexec):
        self.user = uid
        self.uread = uread
        self.uwrite = uwrite
        self.uexec = uexec
        self.group = gid
        self.gread = gread
        self.gwrite = gwrite
        self.gexec = gexec
        self.oread = oread
        self.owrite = owrite
        self.oexec = oexec

    def __str__(self) -> str:
        result = ""
        result += "r" if self.uread else "-"
        result += "w" if self.uwrite else "-"
        result += "x" if self.uexec else "-"
        result += "r" if self.gread else "-"
        result += "w" if self.gwrite else "-"
        result += "x" if self.gexec else "-"
        result += "r" if self.oread else "-"
        result += "w" if self.owrite else "-"
        result += "x" if self.oexec else "-"
        return f'FileRights(user={self.user}   group={self.group}  {result})'
    
    def __repr__(self):
        return str(self)
        

class File:
    def __init__(self, path, file_type):
        self.path = path
        self.file_type = file_type

    def __str__(self) -> str:
        return f'File(path={self.path}, file_type={self.file_type})'
    
    def __repr__(self):
        return str(self)


class ParsingResult:
    ERR_COULD_NOT_PARSE = 0
    WARN_IGNORE_LINE = 1
    OK = 2
    
    
class Event:
    
    def __init__(self, timestamp, description):
        self.event_type: str = type(self).__name__
        self.timestamp: int = timestamp
        self.description: str = description
        
    def __str__(self) -> str:
        return f'Event(timestamp={self.timestamp}, description={self.description})'
    
    def __repr__(self):
        return str(self)
    

class FSEvent(Event):

    def __init__(self, timestamp, description, fd, process):
        super().__init__(timestamp, description)
        self.fd: int = fd
        self.process: Process = process


class OpenEvent(FSEvent):
    
    def __init__(self, timestamp, description, process, file, fd, mode, flags):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.file = file
        self.fd = fd
        self.mode = mode
        self.flags = flags
        
    def __str__(self) -> str:
        return f'OpenEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, file={self.file}, fd={self.fd}, mode={self.mode}, flags={self.flags})'
    
    def __repr__(self):
        return str(self)
    

class CloseEvent(FSEvent):
    
    def __init__(self, timestamp, description, process, fd):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.fd = fd
        
    def __str__(self) -> str:
        return f'CloseEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, fd={self.fd})'
    
    def __repr__(self):
        return str(self)
    
    
class EnterReadEvent(FSEvent):
    
    def __init__(self, timestamp, description, process, fd, size):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.fd = fd
        self.size = size
        
    def __str__(self) -> str:
        return f'EnterReadEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, fd={self.fd}, size={self.size})'
    
    def __repr__(self):
        return str(self)
    

class ExitReadEvent(FSEvent):
    
    def __init__(self, timestamp, description, process, fd, size, content, ret):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.fd = fd
        self.size = size
        self.content = content
        self.ret = ret
        
    def __str__(self) -> str:
        return f'ExitReadEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, fd={self.fd}, size={self.size}, content={self.content}, ret={self.ret})'
    
    def __repr__(self):
        return str(self)
    
    
class WriteEvent(FSEvent):
        
    def __init__(self, timestamp, description, process, fd, size, content):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.fd = fd
        self.size = size
        self.content = content
        
    def __str__(self) -> str:
        return f'WriteEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, fd={self.fd}, size={self.size}, content={self.content})'
    
    def __repr__(self):
        return str(self)


class IPCAModel:
    def __init__(self):
        self.processes: List[Process] = []
        self.channels: List[CommunicationChannel] = []
        self.files: List[File] = []
        self.events: List[FSEvent] = []

    def has_process(self, pid):
        for p in self.processes:
            if p.pid == pid:
                return p
        return None

    def add_or_get_process(self, process):
        old_process = self.has_process(process.pid)
        if old_process:
            process = old_process
        else:
            self.processes.append(process)
        return process

    def has_channel(self, channel):
        for c in self.channels:
            if c.name == channel.name:
                return c
        return None

    def add_or_get_channel(self, channel):
        old_channel = self.has_channel(channel)
        if old_channel:
            channel = old_channel
        else:
            self.channels.append(channel)
        return channel

    def has_file(self, file):
        for f in self.files:
            if f.path == file.path:
                return f
        return None

    def add_or_get_file(self, file):
        old_file = self.has_file(file)
        if old_file:
            file = old_file
        else:
            self.files.append(file)
        return file
    
    def add_event(self, event):
        self.events.append(event)

    def __str__(self) -> str:
        return f'IPCAModel(processes={self.processes}, channels={self.channels}, files={self.files})'
    
    def __repr__(self):
        return str(self)
    

GlobalModel = IPCAModel()