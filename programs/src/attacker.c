
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define OUT_BUFFER_MAX_SIZE 512

static int g_router_fd;
static int g_log_collector_fd;

static char g_out_buffer[OUT_BUFFER_MAX_SIZE];
static int g_out_buffer_size;


int send_message_to_router()
{
    g_out_buffer_size = 0;
    
    printf("Router function selector: \n");
    scanf("%d", (int*) g_out_buffer);
    g_out_buffer_size += 4;

    if((int) g_out_buffer[0] == 0){
        printf("Destination to reach: \n");
        scanf("%d", (int*) &g_out_buffer[4]);
        g_out_buffer_size += 4;
    }

    if((int) g_out_buffer[0] == 1){
        printf("Message to send: \n");
        g_out_buffer_size += read(STDIN_FILENO, &g_out_buffer[4], OUT_BUFFER_MAX_SIZE - 4);
    }
   
    printf("Sending message to router\n");
    printf("Message is ");
    for(int i=0; i<g_out_buffer_size; ++i){
        printf("%x", g_out_buffer[i]);
    }
    printf("\n");
    int n_writen = write(g_router_fd, g_out_buffer, g_out_buffer_size);
    return n_writen > 0;
}


int send_message_to_log_collector()
{
    printf("Sending message to log collector\n");
    strcpy(g_out_buffer, "foup");
    g_out_buffer_size = 4;

    int n_writen = write(g_log_collector_fd, g_out_buffer, g_out_buffer_size);
    return n_writen > 0;
}


int send_message(int destination)
{
    switch(destination){
        case 0:
            return send_message_to_router();
        case 1:
            return send_message_to_log_collector();
        default:
            printf("Wrong destination\n");
            return 1;
    }
    return 0;
}


int choose_target()
{
    printf("Choose target to send message to :\n");
    printf("\t 0: router\n");
    printf("\t 1: log_collector\n");
    
    int target;
    scanf("%d", &target);
    return target;
}


void loop()
{
    while(1){
        
        int target = choose_target();
        (void) send_message(target);
    }
}


void cleanup(char *argv[])
{
    close_fifo(g_router_fd, argv[1]);
    close_fifo(g_log_collector_fd, argv[2]);
}


int main(int argc, char *argv[])
{
    g_router_fd = -1;
    g_log_collector_fd = -1;

    if(argc != 3){
        printf("Usage: %s [router_fifo] [log_collector_fifo]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<2; ++i){
        if(strlen(argv[i+1]) >= PATH_MAX_LEN){
            printf("File path too long : %s\n", argv[i+1]);
            return 1;
        }
    }


    int err;
    err = open_fifo(argv[1], &g_router_fd, O_WRONLY);
    if(err){
        printf("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }
    
    err = open_fifo(argv[2], &g_log_collector_fd, O_WRONLY);
    if(err){
        printf("Could not open fifo %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
