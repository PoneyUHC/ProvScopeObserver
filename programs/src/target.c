
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

static char g_in_msg[IN_BUFFER_MAX_SIZE];
static int g_out_packet_size;



void loop()
{
    while(1){
        
        LOG("Reading input fifo\n");
        g_out_packet_size = read(g_in_fd, g_in_msg, IN_BUFFER_MAX_SIZE);
        if(g_out_packet_size == -1 || g_out_packet_size == 0){
            LOG("Error on read\n");
            sleep(1);
            continue;
        }
        LOG("Received message '%s'\n", g_in_msg);
    }
}


void cleanup(char *argv[])
{
    close_fifo(g_in_fd, argv[1]);
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fd = -1;

    if(argc != 2){
        LOG("Usage: %s [fifo_in]\n", argv[0]);
        return 1;
    }

    if(strlen(argv[1]) >= PATH_MAX_LEN){
        LOG("Fifo path too long : %s\n", argv[1]);
        return 1;
    }

    int err;
    err = open_fifo(argv[1], &g_in_fd, O_RDONLY);
    if(err){
        LOG("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }

    loop();

    cleanup(argv);

    return 0;
}