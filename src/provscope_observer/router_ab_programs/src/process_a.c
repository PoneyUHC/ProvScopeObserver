
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512

static int g_in_fd;           // FIFO to receive messages from router
static char g_in_msg[IN_BUFFER_MAX_SIZE];
static char* g_allow_file_path;


void receive_message()
{
    LOG("Reading input fifo\n");
    
    int msg_size;
    int n_read = read(g_in_fd, &msg_size, 4);
    int err = usual_read_errors(n_read);
    if(err != 0){
        return;
    }
    
    if(msg_size >= IN_BUFFER_MAX_SIZE){
        LOG("Message too large: %d\n", msg_size);
        return;
    }
    
    n_read = read(g_in_fd, g_in_msg, msg_size);
    if(n_read != msg_size){
        LOG("Error: could not read full message (expected %d, got %d)\n", msg_size, n_read);
        return;
    }
    
    g_in_msg[msg_size] = '\0';
    LOG("Received message: %s\n", g_in_msg);
    
    // Write byte '1' to allow file
    int allow_fd = open(g_allow_file_path, O_WRONLY | O_CREAT | O_TRUNC, S_IRUSR | S_IWUSR);
    if(allow_fd == -1){
        LOG("Could not open allow file %s\n", g_allow_file_path);
        return;
    }
    
    char allow_byte = '1';
    write(allow_fd, &allow_byte, 1);
    close(allow_fd);
    
    LOG("Wrote byte '1' to allow file\n");
}


void loop()
{
    while(1){
        receive_message();
        usleep(100000);  // Small delay to avoid busy waiting
    }
}


void cleanup()
{
    close_fifo(g_in_fd);
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fd = -1;

    if(argc != 3){
        LOG("Usage: %s [fifo_in] [allow_file]\n", argv[0]);
        return 1;
    }

    if(strlen(argv[1]) >= PATH_MAX_LEN){
        LOG("Fifo path too long: %s\n", argv[1]);
        return 1;
    }

    if(strlen(argv[2]) >= PATH_MAX_LEN){
        LOG("Allow file path too long: %s\n", argv[2]);
        return 1;
    }

    g_allow_file_path = argv[2];

    // Open input FIFO
    g_in_fd = open(argv[1], O_RDONLY);
    if(g_in_fd == -1){
        LOG("Could not open input fifo %s\n", argv[1]);
        return 2;
    }

    LOG("Process A started, listening for messages\n");
    loop();

    cleanup();

    return 0;
}

