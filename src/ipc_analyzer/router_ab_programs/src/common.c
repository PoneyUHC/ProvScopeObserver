
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
    fflush(stdout);  // Force immediate output, especially important when redirected to file
    fflush(stderr);  // Also flush stderr in case it's being used

    free(timed_format);

    va_end(args);
}

