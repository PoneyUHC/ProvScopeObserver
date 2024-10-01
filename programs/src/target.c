
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512

static int g_in_fd;

static char g_in_buffer[IN_BUFFER_MAX_SIZE];
static int g_buffer_size;



void loop()
{
    while(1){
        
        printf("Reading input fifo\n");
        g_buffer_size = read(g_in_fd, g_in_buffer, IN_BUFFER_MAX_SIZE);
        if(g_buffer_size == -1){
            printf("Error on read\n");
            sleep(1);
            continue;
        }
    }
}


void cleanup(char *argv[])
{
    close_fifo(g_in_fd, argv[1]);
}


int main(int argc, char *argv[])
{
    g_in_fd = -1;

    if(argc != 2){
        printf("Usage: %s [fifo_in]\n", argv[0]);
        return 1;
    }

    if(strlen(argv[1]) >= PATH_MAX_LEN){
        printf("Fifo path too long : %s\n", argv[1]);
        return 1;
    }

    int err;
    err = open_fifo(argv[1], &g_in_fd, O_RDONLY);
    if(err){
        printf("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }

    loop();

    cleanup(argv);

    return 0;
}