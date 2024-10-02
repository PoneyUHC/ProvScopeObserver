
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512
#define LOG_BUFFER_SIZE 512

static int g_STATE_destination;

static int g_in_fd;

#define N_DESTINATION 2
static int g_out_fd[N_DESTINATION];
static int g_log_fd;

static char g_in_buffer[IN_BUFFER_MAX_SIZE];
static int g_out_buffer_size;

static char g_log_buffer[LOG_BUFFER_SIZE];


int API_select_destination()
{
    if(g_out_buffer_size < 8){
        printf("no destination selection specified, aborting parsing\n");
        return 1;
    }

    g_STATE_destination = (int) *(g_in_buffer+4);
    printf("Destination set to %d\n", g_STATE_destination);
    return 0;
}


int API_send_message()
{
    if(g_STATE_destination != 0 && g_STATE_destination != 1){
        printf("Wrong destination\n");
        return 1;
    }
    
    printf("Sending message to %d\n", g_STATE_destination);
    write(g_out_fd[g_STATE_destination], g_in_buffer, g_out_buffer_size);

    sprintf(g_log_buffer, "%d,%d,%s\n", 2, g_STATE_destination, &g_in_buffer[4]);
    write(g_log_fd, g_log_buffer, 4 + g_out_buffer_size - 4);
    
    return 0;
}


int parse_API_function_selection(int *out_selected)
{
    if(g_out_buffer_size < 4){
        printf("no api function specified, aborting parsing\n");
        return -1;
    }

    *out_selected = (int) *g_in_buffer;
    return 0;
}


int dispatch_API_call(int function_id)
{
    switch(function_id){
        case 0:
            return API_select_destination();
        case 1:
            return API_send_message();
        default:
            printf("Wrong selector value\n");
            return 1;
    }
}


void loop()
{
    int err;

    while(1){
        
        printf("Reading input fifo\n");
        g_out_buffer_size = read(g_in_fd, g_in_buffer, IN_BUFFER_MAX_SIZE);
        if(g_out_buffer_size == -1){
            printf("Error on read\n");
            sleep(1);
            continue;
        }

        int selector = 0;
        err = parse_API_function_selection(&selector);
        if(err == -1){
            printf("Error on selector field\n");
            sleep(1);
            continue;
        }

        err = dispatch_API_call(selector);
        if(err){
            printf("Error when dispatching call\n");
            sleep(1);
            continue;
        }
    }
}


void cleanup(char *argv[])
{
    close_fifo(g_in_fd, argv[1]);
    close_fifo(g_out_fd[0], argv[2]);
    close_fifo(g_out_fd[1], argv[3]);
    close(g_log_fd);
}


int main(int argc, char *argv[])
{
    g_in_fd = -1;
    g_log_fd = -1;
    g_out_fd[0] = -1;
    g_out_fd[1] = -1;

    if(argc != 5){
        printf("Usage: %s [fifo_in] [fifo_out] [fifo_out] [filename]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<4; ++i){
        if(strlen(argv[i+1]) >= PATH_MAX_LEN){
            printf("File path too long : %s\n", argv[i+1]);
            return 1;
        }
    }


    int err;
    err = open_fifo(argv[1], &g_in_fd, O_RDONLY);
    if(err){
        printf("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }
    
    err = open_fifo(argv[2], g_out_fd, O_WRONLY | O_CREAT);
    if(err){
        printf("Could not open fifo %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }
    err = open_fifo(argv[3], g_out_fd+1, O_WRONLY | O_CREAT);
    if(err){
        printf("Could not open fifo %s\n", argv[3]);
        cleanup(argv);
        return 2;
    }

    g_log_fd = open(argv[4], O_RDWR | O_CREAT);
    if(g_log_fd == -1){
        printf("Could not open file %s\n", argv[4]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
