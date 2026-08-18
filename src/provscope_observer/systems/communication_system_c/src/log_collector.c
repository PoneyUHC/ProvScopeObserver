
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/epoll.h>
#include <errno.h>
#include <time.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define PARSE_BUFFER_SIZE 4096

static int g_in_fd;

static int g_log_fd;

static int g_goal_fd;

static int g_received_command;

static char g_parse_buffer[PARSE_BUFFER_SIZE];
static int g_parse_buffer_size = 0;

static int read_timer_ms = 50;
static int write_timer_ms = 120;
static long long last_read_ms = 0;
static long long last_write_ms = 0;


int read_and_parse(int fd)
{
    char c;
    int n_read;
    int new_content = 0;
    while(1){
        n_read = read(fd, &c, 1);
        if(n_read <= 0){
            break;
        }

        new_content = 1;

        if(c == ','){
            c = ' ';
        }

        g_parse_buffer[g_parse_buffer_size] = c;
        ++g_parse_buffer_size;

        if(g_parse_buffer_size >= PARSE_BUFFER_SIZE){
            return 1;
        }
    }

    if(!new_content){
        return 0;
    }

    LOG("Content of buffer after parsing :");
    printf("%s\n", g_parse_buffer);

    return 0;
}


// format of log file is 'dest,msg\n' on each line 
int API_read_and_parse(){
    int err;
    err = read_and_parse(g_log_fd);
    if (err){
        LOG("Error reading log file\n");
        return 1;
    }

    return 0;
}


void write_to_goal()
{
    if(g_parse_buffer_size == 0){
        return;
    }
    LOG("Writing '%s' to goal\n", g_parse_buffer);
    write(g_goal_fd, g_parse_buffer, g_parse_buffer_size);

    memset(g_parse_buffer, 0, PARSE_BUFFER_SIZE);
    g_parse_buffer_size = 0;
}


int handle_input()
{
    LOG("Received message: %d\n", g_received_command);

    if(g_received_command != 0){
        LOG("Message not recognized\n");
        return 1;
    } 
    
    return API_read_and_parse();
}


void loop()
{
    int fifos[1] = {g_in_fd};
    int ep = make_epoll(fifos, 1);
    if (ep < 0) {
        LOG("Issue when creating epoll\n");
        return;
    }

    int err;
    int n_read;

    while(1){
        struct epoll_event events[8];
        int n = epoll_wait(ep, events, 8, 1000);
        if (n < 0) {
            if (errno == EINTR) continue;
            LOG("Error on epoll wait\n");
            break;
        }

        if (n > 0 && (events[0].events & EPOLLIN)) {
            LOG("Reading input fifo\n");
            n_read = read(g_in_fd, &g_received_command, 4);

            if(n_read != -1 && n_read != 0){
                err = handle_input();
                if(err){
                    sleep(1);
                }
            }
        }

        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        long long now_ms = ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;

        if(now_ms - last_read_ms > read_timer_ms){
            last_read_ms = now_ms;
            LOG("Read timer expired, reading and parsing log file\n");
            API_read_and_parse();
        }

        if(now_ms - last_write_ms > write_timer_ms){
            last_write_ms = now_ms;
            LOG("Write timer expired, writing parsed data to goal\n");
            write_to_goal();
        }
    }
}


void cleanup()
{
    close_fifo(g_in_fd);
    close(g_goal_fd);

    close(g_log_fd);
}


int open_log_file(char* argv[])
{
    g_log_fd = open(argv[1], O_RDONLY);
    if(g_log_fd == -1){
        LOG("Could not open file %s\n", argv[1]);
        return 2;
    }

    return 0;
}


int create_fifos(char* argv[]) 
{
    int err = create_fifo(argv[2]);
    if(err){
        LOG("Could not create fifo %s\n", argv[2]);
        return 2;
    }

    return 0;
}


int open_in_fifos_non_blocking(char* argv[]) 
{
    g_in_fd = open_fifo_rd(argv[2], 1);
    if(g_in_fd == -1){
        LOG("Could not open fifo %s\n", argv[2]);
        return 2;
    }

    return 0;
}


int open_goal(char* argv[]) 
{
    g_goal_fd = open(argv[3], O_WRONLY | O_CREAT,  S_IRWXU);
    if(g_goal_fd == -1){
        LOG("Could not open file %s\n", argv[3]);
        return 2;
    }

    return 0;
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fd = -1;
    g_goal_fd = -1;
    g_log_fd = -1;
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    last_read_ms = ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;
    last_write_ms = last_read_ms;

    if(argc != 4){
        LOG("Usage: %s [log_file] [fifo_in] [goal_file]\n", argv[0]);
        return 1;
    }

    for(int i=1; i<4; ++i){
        if(strlen(argv[i]) >= PATH_MAX_LEN){
            LOG("File path too long : %s\n", argv[i]);
            return 1;
        }
    }

    if (open_log_file(argv)) cleanup();
    if (create_fifos(argv)) cleanup();
    if (open_in_fifos_non_blocking(argv)) cleanup();
    if (open_goal(argv)) cleanup();
    
    loop();

    cleanup();

    return 0;
}
