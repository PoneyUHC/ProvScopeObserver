
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512
#define LOG_BUFFER_SIZE 512

static int g_STATE_destination;

static int g_in_fd;

#define N_DESTINATION 2
#define ATTACKER_INDEX N_DESTINATION
static int g_out_fd[N_DESTINATION];
static int g_log_fd;

static char g_in_msg[IN_BUFFER_MAX_SIZE];
static int g_in_msg_size;
static int g_in_packet_size;

static char g_log_buffer[LOG_BUFFER_SIZE];

#define ERR_NOTHING_TO_READ 1
#define ERR_READ_ERROR 2
#define ERR_MSG_TOO_SHORT 3
#define ERR_INVALID_SELECTOR_VALUE 4


int usual_read_errors(int n_read)
{
    if (n_read == 0) {
        LOG("Nothing to read\n");
        return ERR_NOTHING_TO_READ;
    }
        
    if(n_read < 0){
        LOG("Error on read\n");
        return ERR_READ_ERROR;
    }
    
    return 0;
}


int API_select_destination()
{
    if(g_in_packet_size < 12){
        read(g_in_fd, g_in_msg, g_in_packet_size - 8);
        LOG("Message too short\n");
        return ERR_MSG_TOO_SHORT;
    }

    int tmp_destination = 0;
    int n_read = read(g_in_fd, &tmp_destination, 4);
    int err = usual_read_errors(n_read);
    if(err){
        return err;
    }

    if(tmp_destination != 0 && tmp_destination != 1) {
        LOG("Invalid destination value\n");
        return 1;
    }

    g_STATE_destination = tmp_destination;

    LOG("Destination set to %d\n", g_STATE_destination);
    return 0;
}


int API_send_message()
{
    int n_read = read(g_in_fd, g_in_msg, g_in_packet_size - 8);
    int err = usual_read_errors(n_read);
    if(err){
        LOG("Packet size and message don't match\n");
        return err;
    }

    LOG("Sending message '%s' to %d\n", g_in_msg, g_STATE_destination);
    write(g_out_fd[g_STATE_destination], g_in_msg, g_in_msg_size);

    g_in_msg[g_in_msg_size] = '\0';

    snprintf(g_log_buffer, 512, "%.1d,%.1d,%s\n", ATTACKER_INDEX, g_STATE_destination, g_in_msg);
    write(g_log_fd, g_log_buffer, 4 + g_in_msg_size + 1);
    
    return 0;
}


int parse_API_function_selection(int *out_selected)
{
    int n_read = read(g_in_fd, out_selected, 4);
    int err = usual_read_errors(n_read);
    if(err){
        return err;
    }

    if(*out_selected != 0 && *out_selected != 1)  {
        LOG("Invalid selector value\n");
        return ERR_INVALID_SELECTOR_VALUE;
    }

    return 0;
}


int parse_packet_size()
{
    int n_read = read(g_in_fd, &g_in_packet_size, 4);
    int err = usual_read_errors(n_read);
    if(err){
        return err;
    }

    if(g_in_packet_size < 9){
        // empty rest of ill formed message
        read(g_in_fd, g_in_msg, g_in_packet_size - 4);
        return ERR_MSG_TOO_SHORT;
    }

    g_in_msg_size = g_in_packet_size - 8;

    return 0;
}


int dispatch_API_call(int function_id)
{
    switch(function_id){
        case 0:
            return API_select_destination();
        case 1:
            return API_send_message();
        default:
            LOG("Wrong selector value\n");
            return 1;
    }
}


void loop()
{
    int err;
    int selector;

    while(1){
        
        LOG("Reading input fifo\n");

        err = parse_packet_size(&g_in_packet_size);
        if(err){
            if(err == ERR_MSG_TOO_SHORT){
                LOG("Message too short\n");
            }
            sleep(1);
            continue;
        }

        err = parse_API_function_selection(&selector);
        if(err){
            if(err == ERR_INVALID_SELECTOR_VALUE){
                LOG("Incorrect function selector\n");
            }
            sleep(1);
            continue;
        }

        err = dispatch_API_call(selector);
        if(err){
            LOG("Error when dispatching call\n");
            sleep(1);
            continue;
        }
    }
}


void cleanup()
{
    close_fifo(g_in_fd);
    close_fifo(g_out_fd[0]);
    close_fifo(g_out_fd[1]);
    close(g_log_fd);
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_STATE_destination = 0;

    g_in_fd = -1;
    g_log_fd = -1;
    g_out_fd[0] = -1;
    g_out_fd[1] = -1;

    if(argc != 5){
        LOG("Usage: %s [fifo_in] [fifo_out] [fifo_out] [filename]\n", argv[0]);
        return 1;
    }

    for(int i=0; i<4; ++i){
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
    
    err = open_fifo(argv[2], g_out_fd, O_WRONLY | O_CREAT);
    if(err){
        LOG("Could not open fifo %s\n", argv[2]);
        cleanup(argv);
        return 2;
    }
    err = open_fifo(argv[3], g_out_fd+1, O_WRONLY | O_CREAT);
    if(err){
        LOG("Could not open fifo %s\n", argv[3]);
        cleanup(argv);
        return 2;
    }

    g_log_fd = open(argv[4], O_RDWR | O_CREAT);
    if(g_log_fd == -1){
        LOG("Could not open file %s\n", argv[4]);
        cleanup(argv);
        return 2;
    }
    
    loop();

    cleanup(argv);

    return 0;
}
