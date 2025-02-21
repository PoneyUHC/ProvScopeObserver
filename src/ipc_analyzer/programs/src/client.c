
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512
#define OUT_BUFFER_MAX_SIZE 512

static int g_my_id;

static int g_talkative;
static int g_n_others;

static long g_next_talk_delay;
static long g_last_talk_time;

static int g_in_fd;
static int g_out_fd;

static char g_in_msg[IN_BUFFER_MAX_SIZE];
static char g_out_msg[OUT_BUFFER_MAX_SIZE];


double get_delay_ns()
{
    return rand() % (long)1e9;
}


long get_time_ns()
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}


void send_select(int target)
{
    int total_size = 12;
    int selector = 0;

    ((int*)g_out_msg)[0] = total_size;
    ((int*)g_out_msg)[1] = selector;
    ((int*)g_out_msg)[2] = target;

    write(g_out_fd, g_out_msg, total_size);
}


void send_message()
{
    int total_size = 20;
    int selector = 1;

    ((int*)g_out_msg)[0] = total_size;
    ((int*)g_out_msg)[1] = selector;
    snprintf(g_out_msg+8, OUT_BUFFER_MAX_SIZE-8, "Hello from %.1d", g_my_id);
    write(g_out_fd, g_out_msg, total_size);
}


void send_message_to_random() 
{
    int target = rand() % g_n_others;
    while( target == g_my_id ){
        target = rand() % g_n_others;
    }

    send_select(target);
    send_message();
}


void loop()
{
    int in_packet_size;

    while(1){
    
        LOG("Reading input fifo\n");
        in_packet_size = read(g_in_fd, g_in_msg, IN_BUFFER_MAX_SIZE);
        if(in_packet_size == -1 || in_packet_size == 0){
            LOG("Error on read\n");
        } else {
            LOG("Received message '%s'\n", g_in_msg);
        }
        
        if(g_talkative) {
            if(g_last_talk_time + g_next_talk_delay < get_time_ns()){
                LOG("Sending message\n");
                send_message_to_random();
                g_last_talk_time = get_time_ns();
                g_next_talk_delay = get_delay_ns();
            }
        }

        usleep(200000);
    }
}


void cleanup()
{
    close_fifo(g_in_fd);
    close_fifo(g_out_fd);
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);
    srand(time(NULL));

    g_in_fd = -1;
    g_out_fd = -1;

    if(argc != 6){
        LOG("Usage: %s [talkative] [fifo_in] [fifo_out] [n_others] [my_id]\n", argv[0]);
        return 1;
    }

    g_talkative = atoi(argv[1]);

    if(strlen(argv[2]) >= PATH_MAX_LEN){
        LOG("Fifo path too long : %s\n", argv[2]);
        return 1;
    }

    if(strlen(argv[3]) >= PATH_MAX_LEN){
        LOG("Fifo path too long : %s\n", argv[3]);
        return 1;
    }

    g_in_fd = open(argv[2], O_RDONLY);
    if(g_in_fd == -1){
        LOG("Could not open input fifo %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }

    int flags = fcntl(g_in_fd, F_GETFL, 0);
    fcntl(g_in_fd, F_SETFL, flags | O_NONBLOCK);

    g_out_fd = open(argv[3], O_WRONLY);
    if(g_out_fd == -1){
        LOG("Could not open input fifo %s\n", argv[3]);
        cleanup(argv);
        return 2;
    }

    g_n_others = atoi(argv[4]);
    g_my_id = atoi(argv[5]);

    g_last_talk_time = get_time_ns();
    g_next_talk_delay = get_delay_ns();
    loop();

    cleanup(argv);

    return 0;
}