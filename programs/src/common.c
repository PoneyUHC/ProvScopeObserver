
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <string.h>


int setup(const char *const path, int *out_fd, char *out_fifo_path)
{
    int path_len = strlen(out_fifo_path);
    if(path_len >= 128){
        return 1;
    }
    
    (void) strncpy(out_fifo_path, path, path_len);
    out_fifo_path[path_len] = '\0';

    if(mkfifo(out_fifo_path, 0666) == -1){
        return 1;
    }

    return *out_fd = open(out_fifo_path, O_RDWR) != -1;
}


void cleanup(int fd, char *fifo_path)
{
    close(fd);
    unlink(fifo_path);
}