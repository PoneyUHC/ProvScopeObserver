
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
    

class ResourceType:
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
        return ResourceType.translation_table.get(octal, ResourceType.UNKNOWN)


    def __str__(self) -> str:
        if self == ResourceType.FIFO:
            return "FIFO"
        elif self == ResourceType.CHAR_DEVICE:
            return "CHAR DEVICE"
        elif self == ResourceType.DIRECTORY:
            return "DIRECTORY"
        elif self == ResourceType.BLOCK_DEVICE:
            return "BLOCK DEVICE"
        elif self == ResourceType.REGULAR_FILE:
            return "REGULAR FILE"
        elif self == ResourceType.SYMLINK:
            return "SYMLINK"
        elif self == ResourceType.SOCKET:
            return "SOCKET"
        else:
            return "UNKNOWN"

    def __repr__(self):
        return str(self)


class ResourceRights:
    
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
        return f'ResourceRights(user={self.user}   group={self.group}  {result})'

    def __repr__(self):
        return str(self)
        

class Resource:
    def __init__(self, path, resource_type):
        self.path = path
        self.resource_type = resource_type

    def __str__(self) -> str:
        return f'Resource(path={self.path}, resource_type={self.resource_type})'

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
    
    def __init__(self, timestamp, description, process, fd, ret):
        super().__init__(timestamp, description, fd, process)
        self.process = process
        self.fd = fd
        self.ret = ret

    def __str__(self) -> str:
        return f'CloseEvent(timestamp={self.timestamp}, description={self.description}, process={self.process}, fd={self.fd}, ret={self.ret})'

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
        self.resources: List[Resource] = []
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

    def has_resource(self, resource):
        for f in self.resources:
            if f.path == resource.path:
                return f
        return None

    def add_or_get_resource(self, resource):
        old_resource = self.has_resource(resource)
        if old_resource:
            resource = old_resource
        else:
            self.resources.append(resource)
        return resource
    
    def add_event(self, event):
        self.events.append(event)

    def __str__(self) -> str:
        return f'IPCAModel(processes={self.processes}, resources={self.resources}, events={self.events})'
    
    def __repr__(self):
        return str(self)
    

GlobalModel = IPCAModel()