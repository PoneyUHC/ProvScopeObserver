
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

#include <sys/epoll.h>


int create_fifo(char *path)
{
    if( access( path, F_OK ) != 0) {
        if(mkfifo(path, 0666) == -1){
            LOG("Could not create fifo %s\n", path);
            return 1;
        }
    }
    
    return 0;
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


int usual_read_errors(int n_read)
{
    if (n_read == 0) {
        LOG("Nothing to read\n");
        return ERR_NOTHING_TO_READ;
    }
        
    if(n_read < 0){
        LOG("Error on read\n");
        return ERR_READ_ERROR;
    }
    
    return 0;
}


void LOG(const char *format, ...)
{
    va_list args;
    va_start(args, format);

    char* timed_format = (char*) malloc(11 + strlen(format) + 1);
    get_time_str(timed_format);
    strcat(timed_format, format);
    
    vprintf(timed_format, args);
    fflush(stdout);
    fflush(stderr);

    free(timed_format);

    va_end(args);
}


int open_fifo_rd(const char *path, int nonblock)
{
    int flags = O_RDONLY;
    if(nonblock) flags |= O_NONBLOCK;
    return open(path, flags);
}


int open_fifo_wr(const char *path)
{
    return open(path, O_WRONLY);
}


int make_epoll(const int *fifos, size_t n_fifos)
{
    int ep = epoll_create1(0);
    for (int i=0; i<n_fifos; ++i) {
        struct epoll_event ev;
        ev.events = EPOLLIN;
        ev.data.u32 = i;  // store index so we know which FIFO it was
        if (epoll_ctl(ep, EPOLL_CTL_ADD, fifos[i], &ev) < 0) {
            LOG("Error creating epoll for fifo %d", i);
            return -1;
        }
    }

    return ep;
}