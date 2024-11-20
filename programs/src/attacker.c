
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

static char g_out_packet[OUT_BUFFER_MAX_SIZE];
static int g_out_packet_size;


int send_message_to_router()
{
    g_out_packet_size = 4;

    LOG("Router function selector: \n");
    scanf("%d", ((int*)g_out_packet) + 1);
    g_out_packet_size += 4;


    int selector = ((int*)g_out_packet)[1];
    if(selector == 0){
        LOG("Destination to reach: \n");
        scanf("%d", ((int*)g_out_packet) + 2);
        g_out_packet_size += 4;
    }

    if(selector == 1){
        LOG("Message to send: \n");
        g_out_packet_size += read(STDIN_FILENO, g_out_packet+8, OUT_BUFFER_MAX_SIZE - 8);
        // Remove '\n'
        --g_out_packet_size;
    }

    

    ((int*)g_out_packet)[0] = g_out_packet_size;
   
    LOG("Sending message to router\n");
    LOG("Message is ");
    for(int i=0; i<g_out_packet_size; ++i){
        printf("%.2x", g_out_packet[i]);
    }
    printf("\n");
    int n_writen = write(g_router_fd, g_out_packet, g_out_packet_size);
    return n_writen > 0;
}


int send_message_to_log_collector()
{
    LOG("Sending message to log collector\n");
    *g_out_packet = 0;
    g_out_packet_size = 1;

    int n_writen = write(g_log_collector_fd, g_out_packet, g_out_packet_size);
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
            LOG("Wrong destination\n");
            return 1;
    }
    return 0;
}


int choose_target()
{
    LOG("Choose target to send message to :\n");
    LOG("\t 0: router\n");
    LOG("\t 1: log_collector\n");
    
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


void cleanup()
{
    close_fifo(g_router_fd);
    close_fifo(g_log_collector_fd);
}


int main(int argc, char *argv[])
{
    g_router_fd = -1;
    g_log_collector_fd = -1;

    if(argc != 3){
        LOG("Usage: %s [router_fifo] [log_collector_fifo]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<2; ++i){
        if(strlen(argv[i+1]) >= PATH_MAX_LEN){
            LOG("File path too long : %s\n", argv[i+1]);
            return 1;
        }
    }


    int err;
    err = open_fifo(argv[1], &g_router_fd, O_WRONLY);
    if(err){
        LOG("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }
    
    err = open_fifo(argv[2], &g_log_collector_fd, O_WRONLY);
    if(err){
        LOG("Could not open fifo %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
