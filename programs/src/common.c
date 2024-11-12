
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <stdio.h>
#include <string.h>


int open_fifo(char *path, int *out_fd, int mode)
{
    if(mode == O_RDONLY){
        if(mkfifo(path, 0666) == -1){
            printf("Could not create fifo %s\n", path);
            return 1;
        }
    }
    
    *out_fd = open(path, mode);

    return *out_fd == -1;
}


void close_fifo(int fd, char *fifo_path)
{
    close(fd);
}