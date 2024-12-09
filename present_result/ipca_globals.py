
class Process:
    def __init__(self, pid, name):
        self.pid = pid
        self.name = name
        self.open_infos = []
        self.communication_infos = []

    def __str__(self):
        return f'Process(pid={self.pid}, name={self.name}, open_infos={self.open_infos}, communication_infos={self.communication_infos})'
    
    def __repr__(self):
        return str(self)
    
    def add_open_info(self, open_info):
        self.open_infos.append(open_info)

    def add_communication_info(self, communication_info):
        self.communication_infos.append(communication_info)

    def get_unclosed_open_info(self, fd):
        for open_info in self.open_infos:
            if open_info.fd == fd and open_info.close_time == -1:
                return open_info
        
        missing_open_time = OpenInfo(-1, -1, None, fd, -1, -1)
        self.open_infos.append(missing_open_time)
        return missing_open_time 
    
    def get_open_info_at_time(self, fd, timestamp):
        for open_info in self.open_infos:
            if (open_info.fd == fd 
                and open_info.open_time <= timestamp 
                and (open_info.close_time > timestamp 
                     or open_info.close_time == -1)):
                return open_info
        return None


class ChannelType:
    FIFO = 0
    PIPE = 1
    SOCKET = 2

    def __str__(self) -> str:
        if self == ChannelType.FIFO:
            return "FIFO"
        elif self == ChannelType.PIPE:
            return "PIPE"
        elif self == ChannelType.SOCKET:
            return "SOCKET"
        else:
            return "UNKNOWN"
        
    def __repr__(self):
        return str(self)


class CommunicationChannel:
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self) -> str:
        return f'CommunicationChannel(name={self.name}, type={self.type})'
    
    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        return self.name == other.name and self.type == other.type


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
    def __init__(self, path, rights):
        self.path = path
        self.rights = rights

    def __str__(self) -> str:
        return f'File(path={self.path}, rights={self.rights})'
    
    def __repr__(self):
        return str(self)
    

class OpenInfo:
    def __init__(self, open_time, close_time, file, fd, mode, flags):
        self.open_time = open_time
        self.close_time = close_time
        self.file = file
        self.fd = fd
        self.mode = mode
        self.flags = flags

    def __str__(self) -> str:
        return f'OpenInfo(open_time={self.open_time}, close_time={self.close_time}, file={self.file}, fd={self.fd}, mode={self.mode}, flags={self.flags})'
    
    def __repr__(self):
        return str(self)


class ParsingResult:
    ERR_COULD_NOT_PARSE = 0
    WARN_IGNORE_LINE = 1
    OK = 2


class IPCAModel:
    def __init__(self):
        self.processes = []
        self.channels = []
        self.files = []

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

    def add_channel(self, channel):
        self.channels.append(channel)

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

    def __str__(self) -> str:
        return f'IPCAModel(processes={self.processes}, channels={self.channels}, files={self.files})'
    
    def __repr__(self):
        return str(self)
    
GlobalModel = IPCAModel()