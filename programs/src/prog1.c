
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256

static int g_rb;
static int g_in_fd;
static int g_out_fd;


void API_function_1(int value)
{
    g_rb += value; 
}


void API_function_2(int value)
{
    g_rb -= value;
    int out_buffer[2];
}


int API_function_dispatch(int selector, int parameter)
{

    switch(selector){
        case 0:
            API_function_1(parameter);
            break;
        case 1:
            API_function_2(parameter);
            break;
        default:
            printf("Wrong selector value\n");
            return 1;
    }
    return 0;
}


int listen(int in_buffer[2])
{   
    printf("Reading input fifo\n");
    int n_read = read(g_in_fd, in_buffer, 2);
    return 0;
}


int work(int in_buffer[2])
{
    int function_selector = in_buffer[0];
    int function_parameter = in_buffer[1];
    int err = API_function_dispatch(function_selector, function_parameter);
    return err;
}


void loop()
{
    int err;
    int in_buffer[2];

    while(1){
        err = listen(in_buffer);
        if(err){
            sleep(1);
            continue;
        }

        err = work(in_buffer);
        if(err){
            printf("Invalid input received, ignoring\n");
            sleep(1);
            continue;
        }
    }
}


int main(int argc, char *argv[])
{
    if(argc != 3){
        printf("Usage: %s [fifo] [filename]\n", argv[0]);
        return 1;
    }

    if(strlen(argv[1]) >= PATH_MAX_LEN){
        printf("Fifo path too long : %s\n", argv[1]);
        return 1;
    }

    if(strlen(argv[2]) >= PATH_MAX_LEN){
        printf("Filename path too long : %s\n", argv[2]);
        return 1;
    }


    int err;
    err = open_fifo(argv[1], &g_in_fd);
    printf("%d\n", g_in_fd);
    printf("%d\n", err);
    if(err){
        return 2;
    }
    
    g_out_fd = open(argv[2], O_RDWR);
    if(err == -1){
        close_fifo(g_in_fd, argv[1]);
        return 3;
    }

    
    loop();


    close_fifo(g_in_fd, argv[1]);
}
