
class Process:
    def __init__(self, pid, name):
        self.pid = pid
        self.name = name
        self.open_infos = []

    def __str__(self):
        return f'Process(pid={self.pid}, name={self.name}, open_infos={self.open_infos})'
    
    def __repr__(self):
        return str(self)
    
    def open_file(self, open_info):
        self.open_infos.append(open_info)


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
    def __init__(self, name, file, readers, writers, type):
        self.name = name
        self.file = file
        self.readers = readers
        self.writers = writers
        self.type = type

    def __str__(self) -> str:
        return f'CommunicationChannel(name={self.name}, file={self.file}, readers={self.readers}, writers={self.writers}, type={str(self.type)})'
    
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
        return f'FileRights({result}, user={self.user}, group={self.group})'
    
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
    def __init__(self, file, fd, mode, flags):
        self.file = file
        self.fd = fd
        self.mode = mode
        self.flags = flags

    def __str__(self) -> str:
        return f'OpenInfo(file={self.file} fd={self.fd}, mode={self.mode}, flags={self.flags})'
    
    def __repr__(self):
        return str(self)


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

    def add_or_get_channel(self, channel):
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