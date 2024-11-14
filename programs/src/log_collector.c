
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define PARSE_BUFFER_SIZE 1024

static int g_in_fd;
static int g_log_fd;
static int g_goal_fd;

static int g_received_command;

static char g_parse_buffer[PARSE_BUFFER_SIZE];
static int g_parse_buffer_size = 0;

static int read_timer = 4;
static int write_timer = 10;
static int last_read_date = 0;
static int last_write_date = 0;

// format of log file is 'src,dest,msg\n' on each line 
int API_read_and_parse(){
    char c;
    int n_read;
    int new_content = 0;
    while(1){
        n_read = read(g_log_fd, &c, 1);
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

    int flags = fcntl(g_in_fd, F_GETFL, 0);
    fcntl(g_in_fd, F_SETFL, flags | O_NONBLOCK);

    while(1){
        
        LOG("Reading input fifo\n");
        n_read = read(g_in_fd, &g_received_command, 4);

        if(n_read != -1 && n_read != 0){
            err = handle_input();
            if(err){
                sleep(1);
            }
        } else {
            LOG("Nothing to read\n");
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


void cleanup(char *argv[])
{
    close_fifo(g_in_fd, argv[1]);
    close(g_goal_fd);
    close(g_log_fd);
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fd = -1;
    g_goal_fd = -1;
    g_log_fd = -1;
    last_read_date = time(NULL);

    if(argc != 4){
        LOG("Usage: %s [fifo_in] [log_file] [goal_file]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<3; ++i){
        if(strlen(argv[i+1]) >= PATH_MAX_LEN){
            LOG("File path too long : %s\n", argv[i+1]);
            return 1;
        }
    }


    int err;
    err = open_fifo(argv[1], &g_in_fd, O_RDONLY);
    if(err){
        LOG("Could not open fifo %s\n", argv[1]);
        cleanup(argv);
        return 2;
    }
    
    g_log_fd = open(argv[2], O_RDWR | O_CREAT);
    if(g_log_fd == -1){
        LOG("Could not open file %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }

    g_goal_fd = open(argv[3], O_RDWR | O_CREAT);
    if(g_goal_fd == -1){
        LOG("Could not open file %s\n", argv[3]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
