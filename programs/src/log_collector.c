
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define OUT_BUFFER_MAX_SIZE 512
#define PARSE_BUFFER_SIZE 1024

static int g_in_fd;
static int g_log_fd;
static int g_goal_fd;

static char g_in_buffer[OUT_BUFFER_MAX_SIZE];
static int g_buffer_size = 0;

static char g_parse_buffer[PARSE_BUFFER_SIZE];
static int g_parse_buffer_size = 0;

static int read_timer = 2;
static int write_timer = 10;
static int last_read_date = 0;
static int last_write_date = 0;

// format of log file is 'src,dest,msg\n' on each line 
int API_read_and_parse(){
    g_parse_buffer_size = 0;
    char c;
    int n_read;
    while(1){
        n_read = read(g_log_fd, &c, 1);
        if(!n_read ){
            break;
        }

        if(c == ','){
            c = ' ';
        }

        g_parse_buffer[g_parse_buffer_size] = c;
        g_parse_buffer_size += 1;

        if(g_parse_buffer_size >= PARSE_BUFFER_SIZE){
            return 1;
        }
    }

    return 0;
}


void write_to_goal()
{
    write(g_goal_fd, g_parse_buffer, g_parse_buffer_size);
}


int handle_input()
{
    if(g_buffer_size != 5 || strcmp(g_in_buffer, "foup") != 0){
        return 1;
    } 
    
    return API_read_and_parse();
}


void loop()
{
    int err;

    while(1){
        
        printf("Reading input fifo\n");
        g_buffer_size = read(g_in_fd, g_in_buffer, OUT_BUFFER_MAX_SIZE);
        if(g_buffer_size == -1){
            printf("Error on read\n");
            sleep(1);
            continue;
        }

        err = handle_input();
        if(err){
            printf("Message not recognized\n");
            sleep(1);
            continue;
        }

        int actual_date = time(NULL);
        if(actual_date - last_read_date > read_timer){
            last_read_date = actual_date;
            API_read_and_parse();
        }

        if(actual_date - last_write_date > write_timer){
            last_write_date = actual_date;
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
    g_in_fd = -1;
    g_goal_fd = -1;
    g_log_fd = -1;
    last_read_date = time(NULL);

    if(argc != 4){
        printf("Usage: %s [fifo_in] [log_file] [goal_file]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<3; ++i){
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
    
    g_log_fd = open(argv[2], O_RDWR | O_CREAT);
    if(g_log_fd == -1){
        printf("Could not open file %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }

    g_goal_fd = open(argv[3], O_RDWR | O_CREAT);
    if(g_goal_fd == -1){
        printf("Could not open file %s\n", argv[3]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
