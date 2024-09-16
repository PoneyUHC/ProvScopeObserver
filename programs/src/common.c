
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <string.h>


int open_fifo(char *path, int *out_fd)
{
    if(mkfifo(path, 0666) == -1){
        return 1;
    }

    return *out_fd = open(path, O_RDWR) == -1;
}


void close_fifo(int fd, char *fifo_path)
{
    close(fd);
    unlink(fifo_path);
}