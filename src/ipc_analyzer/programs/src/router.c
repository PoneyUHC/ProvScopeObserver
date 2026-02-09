
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
#define OUT_BUFFER_MAX_SIZE 512
#define LOG_BUFFER_SIZE 512

static int* g_STATE_destinations;
static int g_STATE_token_owner;

static int g_n_targets;
static int *g_out_fds;
static int *g_in_fds;
static int g_log_fd;

static char g_in_msg[IN_BUFFER_MAX_SIZE];
static int g_in_msg_size;
static int g_in_packet_size;

static char g_out_msg[OUT_BUFFER_MAX_SIZE];

static char g_log_buffer[LOG_BUFFER_SIZE];


#define ERR_MSG_TOO_SHORT 3
#define ERR_INVALID_SELECTOR_VALUE 4



int API_select_destination(int in_fd)
{
    if(g_in_packet_size < 12){
        read(in_fd, g_in_msg, g_in_packet_size - 8);
        LOG("Message too short\n");
        return ERR_MSG_TOO_SHORT;
    }

    int tmp_destination = 0;
    int n_read = read(in_fd, &tmp_destination, 4);
    int err = usual_read_errors(n_read);
    if(err){
        return err;
    }

    g_STATE_destinations[g_STATE_token_owner] = tmp_destination;

    LOG("Destination set to %d for client %d\n", g_STATE_destinations[g_STATE_token_owner], g_STATE_token_owner);
    return 0;
}


int API_send_message(int in_fd, int out_fd)
{
    int n_read = read(in_fd, g_in_msg, g_in_packet_size - 8);
    int err = usual_read_errors(n_read);
    if(err){
        LOG("Packet size and message don't match\n");
        return err;
    }

    LOG("Sending message '%s' to %d\n", g_in_msg, g_STATE_destinations[g_STATE_token_owner]);

    ((int*)g_out_msg)[0] = g_in_msg_size;
    strcpy(g_out_msg + 4, g_in_msg);
    write(out_fd, g_out_msg, g_in_msg_size + 4);

    g_in_msg[g_in_msg_size] = '\0';

    snprintf(g_log_buffer, 512, "%.1d,%s\n", g_STATE_destinations[g_STATE_token_owner], g_in_msg);
    write(g_log_fd, g_log_buffer, 2 + g_in_msg_size + 1);
    
    return 0;
}


int parse_API_function_selection(int in_fd, int *out_selected)
{
    int n_read = read(in_fd, out_selected, 4);
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


int parse_packet_size(int in_fd)
{
    int n_read = read(in_fd, &g_in_packet_size, 4);
    int err = usual_read_errors(n_read);
    if(err){
        return err;
    }

    if(g_in_packet_size < 9){
        // empty rest of ill formed message
        read(in_fd, g_in_msg, g_in_packet_size - 4);
        return ERR_MSG_TOO_SHORT;
    }

    g_in_msg_size = g_in_packet_size - 8;

    return 0;
}


int dispatch_API_call(int function_id, int in_fd, int out_fd)
{
    switch(function_id){
        case 0:
            return API_select_destination(in_fd);
        case 1:
            return API_send_message(in_fd, out_fd);
        default:
            LOG("Wrong selector value\n");
            return 1;
    }
}


int consume_token(int in_fd, int out_fd)
{
    int err;
    int selector;

    LOG("Reading input fifo\n");

    err = parse_packet_size(in_fd);
    if(err){
        if(err == ERR_MSG_TOO_SHORT){
            LOG("Message too short\n");
        }
        return 1;
    }

    err = parse_API_function_selection(in_fd, &selector);
    if(err){
        if(err == ERR_INVALID_SELECTOR_VALUE){
            LOG("Incorrect function selector\n");
        }
        return 1;
    }

    err = dispatch_API_call(selector, in_fd, out_fd);
    if(err){
        LOG("Error when dispatching call\n");
        return 1;
    }

    return 0;
}


void loop() 
{

    int n_errors = 0;
    while(1){
        for(int i=0; i<g_n_targets; ++i){
            n_errors += consume_token(g_in_fds[g_STATE_token_owner], g_out_fds[g_STATE_destinations[g_STATE_token_owner]]);
            g_STATE_token_owner = (g_STATE_token_owner + 1) % g_n_targets;
        }

        // Commented to make the router run max speed
        if(n_errors == g_n_targets) {
            LOG("Complete turn with errors, sleeping\n");
            usleep(200000);
        }

        n_errors = 0;
    }
}


void cleanup()
{
    close(g_log_fd);

    for(int i=0; i<g_n_targets; ++i){
        close_fifo(g_out_fds[i]);
        close_fifo(g_in_fds[i]);
    }
    free(g_in_fds); 
    free(g_out_fds);
}


int open_log_file(char* argv[]) 
{
    g_log_fd = open(argv[2], O_WRONLY | O_CREAT, S_IRWXU);
    if(g_log_fd == -1){
        LOG("Could not open file %s\n", argv[2]);
        return 2;
    }

    return 0;
}


int create_fifos(char* argv[]) 
{
    int err;
    for(int i=0; i<2*g_n_targets; ++i){
        err = create_fifo(argv[3+i]);
        if(err){
            LOG("Could not create fifo %s\n", argv[3+i]);
            return 2;
        }
    }

    return 0;
}


int open_out_fifos(char* argv[]) 
{
    for(int i=0; i<g_n_targets; ++i){
        g_out_fds[i] = open(argv[3+g_n_targets+i], O_WRONLY);
        if(g_out_fds[i] == -1){
            LOG("Could not open fifo %s\n", argv[3+g_n_targets+i]);
            return 2;
        }
    }

    return 0;
}


int open_in_fifos_non_blocking(char* argv[]) 
{
    for(int i=0; i<g_n_targets; ++i){
        g_in_fds[i] = open(argv[3+i], O_RDONLY);
        if(g_in_fds[i] == -1){
            LOG("Could not open fifo %s\n", argv[3+i]);
            return 2;
        }
    }

    for(int i=0; i<g_n_targets; ++i){
        int flags = fcntl(g_in_fds[i], F_GETFL, 0);
        fcntl(g_in_fds[i], F_SETFL, flags | O_NONBLOCK);
    }

    return 0;
}



int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    g_in_fds = NULL;
    g_out_fds = NULL;
    
    g_log_fd = -1;

    if(argc < 4) {
        LOG("Usage: %s [n_targets] [log_filename] [fifo_in]* [fifo_out]*\n", argv[0]);
        return 1;
    }

    g_n_targets = atoi(argv[1]);
    if(g_n_targets < 2 || g_n_targets > 6){
        LOG("Number of targets must be at least 2, at most 5\n");
        return 1;
    }

    g_in_fds = (int*) malloc(g_n_targets * sizeof(int));
    g_out_fds = (int*) malloc(g_n_targets * sizeof(int));
    
    g_STATE_destinations = malloc(g_n_targets * sizeof(int));
    for(int i=0; i<g_n_targets; ++i) {
        // default is you speak to yourself
        g_STATE_destinations[i] = i;
    }

    if(argc != 3+2*g_n_targets){
        LOG("Usage: %s [n_targets] [log_filename] [fifo_in]* [fifo_out]* \n", argv[0]);
        return 1;
    }

    
    for(int i=2; i<3+2*g_n_targets; ++i){
        if(strlen(argv[i]) >= PATH_MAX_LEN){
            LOG("File path too long : %s\n", argv[i]);
            return 1;
        }
    }

    
    if (open_log_file(argv)) cleanup();
    if (create_fifos(argv)) cleanup();
    if (open_out_fifos(argv)) cleanup();
    if (open_in_fifos_non_blocking(argv)) cleanup();


    loop();

    cleanup();

    return 0;
}
