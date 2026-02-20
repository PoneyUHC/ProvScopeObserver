
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

static int g_talk_delay_ms;
static int g_my_id;
static int g_petitfilou;
static int g_talk_count;

static int g_n_clients;

static long g_next_talk_delay;
static long g_last_talk_time;

static int g_in_fd;
static int g_out_fd;

static int g_in_msg_size;
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


void send_select(int target, int used_id)
{
    int total_size = 16;
    int selector = 0;

    ((int*)g_out_msg)[0] = total_size;
    ((int*)g_out_msg)[1] = selector;
    ((int*)g_out_msg)[2] = used_id;
    ((int*)g_out_msg)[3] = target;

    write(g_out_fd, g_out_msg, total_size);
    LOG("Selecting client %d\n", target);
}


void send_message(int used_id)
{
    int total_size = 24;
    int selector = 1;

    ((int*)g_out_msg)[0] = total_size;
    ((int*)g_out_msg)[1] = selector;
    ((int*)g_out_msg)[2] = used_id;
    snprintf(g_out_msg+12, 13, "Hello from %.1d", used_id);
    write(g_out_fd, g_out_msg, total_size);

    LOG("Sending message '%s'\n", g_out_msg+12);
}


void send_message_to_random() 
{
    int target;
    do {
        target = rand() % g_n_clients;
    } while( target == g_my_id);

    int used_id = g_my_id;
    if(g_petitfilou) {
        if(g_talk_count % 15 == 0){
            used_id = 9;
        }
    }
    send_select(target, used_id);
    send_message(used_id);

    ++g_talk_count;
}


void receive_message()
{
    LOG("Reading input fifo\n");
    int msg_size = read(g_in_fd, &g_in_msg_size, 4);
    int err = usual_read_errors(msg_size);
    if(err != 0){
        return;
    }
    
    int read_size = read(g_in_fd, g_in_msg, g_in_msg_size);
    if( read_size == msg_size){
        LOG("Error: cannot read enough bytes\n");
        return;
    }
    
    LOG("Received message of %d characters: %s\n", g_in_msg_size, g_in_msg);
}


void loop()
{
    while(1){
    
        receive_message();
        
        if(g_last_talk_time + g_next_talk_delay < get_time_ns()){
            LOG("Sending message\n");
            send_message_to_random();
            g_last_talk_time = get_time_ns();
            g_next_talk_delay = get_delay_ns();
        }

        usleep(g_talk_delay_ms);
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

    // 1 not to trigger the special behavior at start
    g_talk_count = 10;

    if(argc != 7){
        LOG("Usage: %s [petitfilou] [fifo_in] [fifo_out] [n_clients] [my_id] [talk_delay_ms]\n", argv[0]);
        return 1;
    }

    g_petitfilou = atoi(argv[1]);

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
        cleanup();
        return 2;
    }

    int flags = fcntl(g_in_fd, F_GETFL, 0);
    fcntl(g_in_fd, F_SETFL, flags | O_NONBLOCK);

    g_out_fd = open(argv[3], O_WRONLY);
    if(g_out_fd == -1){
        LOG("Could not open input fifo %s\n", argv[3]);
        cleanup();
        return 2;
    }

    g_n_clients = atoi(argv[4]);
    g_my_id = atoi(argv[5]);
    g_talk_delay_ms = atoi(argv[6]);

    g_last_talk_time = get_time_ns();
    g_next_talk_delay = get_delay_ns();
    loop();

    cleanup();

    return 0;
}