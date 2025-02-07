
#include "common.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <stdio.h>
#include <string.h>

#include <stdarg.h>
#include <stdlib.h>
#include <time.h>


int open_fifo(char *path, int *out_fd, int mode)
{
    if(mode == O_RDONLY){
        if(mkfifo(path, 0666) == -1){
            LOG("Could not create fifo %s\n", path);
            return 1;
        }
    }
    
    *out_fd = open(path, mode);

    return *out_fd == -1;
}


void close_fifo(int fd)
{
    close(fd);
}


void get_time_str(char *destination)
{
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    snprintf(destination, 12, "[%02d:%02d:%02d] ", tm.tm_hour, tm.tm_min, tm.tm_sec);
}


void LOG(const char *format, ...)
{
    va_list args;
    va_start(args, format);

    char* timed_format = (char*) malloc(11 + strlen(format) + 1);
    get_time_str(timed_format);
    strcat(timed_format, format);
    
    vprintf(timed_format, args);

    free(timed_format);

    va_end(args);
}