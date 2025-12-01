
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
#define PARSE_BUFFER_SIZE 1024

static int g_in_fd;

static int g_n_logs;
static int *g_log_fds;

static int g_goal_fd;

static int g_received_command;

static char g_parse_buffer[PARSE_BUFFER_SIZE];
static int g_parse_buffer_size = 0;

static int read_timer = 2;
static int write_timer = 4;
static int last_read_date = 0;
static int last_write_date = 0;


int read_and_parse(int fd)
{
    char c;
    int n_read;
    int new_content = 0;
    while(1){
        n_read = read(fd, &c, 1);
        if(!n_read ){
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
    for(int i=0; i<g_n_logs; ++i){
        err = read_and_parse(g_log_fds[i]);
        if (err){
            LOG("Error reading log file %d\n", i);
            return 1;
        }
    }

    return 0;
}


void write_to_goal()
{
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
    int err;
    int n_read;

    while(1){
        
        LOG("Reading input fifo\n");
        n_read = read(g_in_fd, &g_received_command, 4);

        if(n_read != -1 && n_read != 0){
            err = handle_input();
            if(err){
                sleep(1);
            }
        } else {
            /* nothing to read: back off without logging to avoid spam */
            sleep(1);
        }

        int actual_date = time(NULL);
        if(actual_date - last_read_date > read_timer){
            last_read_date = actual_date;
            LOG("Read timer expired, reading and parsing log file\n");
            API_read_and_parse();
        }

        if(actual_date - last_write_date > write_timer){
            last_write_date = actual_date;
            LOG("Write timer expired, writing parsed data to goal\n");
            write_to_goal();
        }
    }
}


void cleanup()
{
    close_fifo(g_in_fd);
    close(g_goal_fd);

    for(int i=0; i<g_n_logs; ++i){
        close(g_log_fds[i]);
    }
}


int open_logs(char* argv[])
{
    g_log_fds = (int*) malloc(g_n_logs * sizeof(int));
    for(int i=0; i<g_n_logs; ++i){
        g_log_fds[i] = open(argv[2+i], O_RDONLY);
        if(g_log_fds[i] == -1){
            LOG("Could not open file %s\n", argv[2+i]);
            return 2;
        }
    }

    return 0;
}


int create_fifos(char* argv[]) 
{
    int err = create_fifo(argv[2+g_n_logs]);
    if(err){
        LOG("Could not create fifo %s\n", argv[2+g_n_logs]);
        return 2;
    }

    return 0;
}


int open_in_fifos_non_blocking(char* argv[]) 
{
    g_in_fd = open(argv[2+g_n_logs], O_RDONLY);
    if(g_in_fd == -1){
        LOG("Could not open fifo %s\n", argv[1]);
        return 2;
    }

    int flags = fcntl(g_in_fd, F_GETFL, 0);
    fcntl(g_in_fd, F_SETFL, flags | O_NONBLOCK);

    return 0;
}


int open_goal(char* argv[]) 
{
    g_goal_fd = open(argv[2+g_n_logs+1], O_WRONLY | O_CREAT,  S_IRWXU);
    if(g_goal_fd == -1){
        LOG("Could not open file %s\n", argv[2+g_n_logs+1]);
        return 2;
    }

    return 0;
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fd = -1;
    g_goal_fd = -1;
    g_log_fds = NULL;
    last_read_date = time(NULL);

    if(argc < 5){
        LOG("Usage: %s [n_logs] [log_file]* [fifo_in] [goal_file]\n", argv[0]);
        return 1;
    }

    g_n_logs = atoi(argv[1]);
    if(argc != 2 + g_n_logs + 2){
        LOG("Usage: %s [n_logs] [log_file]* [fifo_in] [goal_file]\n", argv[0]);
        return 1;
    }

    for(int i=2; i<2+g_n_logs; ++i){
        if(strlen(argv[i]) >= PATH_MAX_LEN){
            LOG("File path too long : %s\n", argv[i]);
            return 1;
        }
    }

    
    if (open_logs(argv)) cleanup();
    if (create_fifos(argv)) cleanup(argv);
    if (open_in_fifos_non_blocking(argv)) cleanup(argv);
    if (open_goal(argv)) cleanup(argv);
    
    loop();

    cleanup(argv);

    return 0;
}
