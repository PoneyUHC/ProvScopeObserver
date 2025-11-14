
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

#include "common.h"


#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512
#define OUT_BUFFER_MAX_SIZE 512

#define TARGET_A 0
#define TARGET_B 1

static int g_current_target;  // 0 for A, 1 for B

static int g_request_fd;      // FIFO to receive requests
static int g_to_a_fd;         // FIFO to send to process A
static int g_to_b_fd;         // FIFO to send to process B

static char g_out_msg[OUT_BUFFER_MAX_SIZE];


#define ERR_MSG_TOO_SHORT 3
#define ERR_INVALID_COMMAND 4


int handle_choose_target(const char* line)
{
    // Line format: "choose_target A" or "choose_target B"
    // Find the space after "choose_target"
    const char* space = strchr(line, ' ');
    if(space == NULL || space[1] == '\0'){
        LOG("Invalid choose_target format\n");
        return ERR_INVALID_COMMAND;
    }
    
    char target_char = space[1];  // Character after the space
    
    if(target_char == 'A' || target_char == 'a'){
        g_current_target = TARGET_A;
        LOG("Target set to A\n");
    } else if(target_char == 'B' || target_char == 'b'){
        g_current_target = TARGET_B;
        LOG("Target set to B\n");
    } else {
        LOG("Invalid target: %c (expected A or B)\n", target_char);
        return ERR_INVALID_COMMAND;
    }

    return 0;
}


int handle_send_message(const char* line)
{
    // Line format: "send_message <message>"
    // Find the space after "send_message"
    const char* space = strchr(line, ' ');
    if(space == NULL || space[1] == '\0'){
        LOG("handle_send_message: Invalid format (no message)\n");
        return ERR_INVALID_COMMAND;
    }
    
    const char* message = space + 1;  // Message starts after the space
    
    // Determine which FIFO to write to
    int target_fd = (g_current_target == TARGET_A) ? g_to_a_fd : g_to_b_fd;
    const char* target_name = (g_current_target == TARGET_A) ? "A" : "B";
    
    LOG("handle_send_message: Sending to target %s (fd=%d)\n", target_name, target_fd);
    
    // Send message to selected target
    int msg_len = strlen(message);
    LOG("handle_send_message: Message length: %d\n", msg_len);
    
    if(msg_len >= IN_BUFFER_MAX_SIZE - 4){
        LOG("handle_send_message: Message too long (%d >= %d)\n", msg_len, IN_BUFFER_MAX_SIZE - 4);
        return ERR_MSG_TOO_SHORT;
    }
    
    ((int*)g_out_msg)[0] = msg_len;
    strcpy(g_out_msg + 4, message);
    
    LOG("handle_send_message: Writing %d bytes to fd %d\n", msg_len + 4, target_fd);
    int n_written = write(target_fd, g_out_msg, msg_len + 4);
    if(n_written == -1){
        LOG("handle_send_message: Write failed (errno: %d)\n", errno);
        return ERR_READ_ERROR;
    }
    LOG("handle_send_message: Wrote %d bytes\n", n_written);
    LOG("handle_send_message: Sent message '%s' to process %s\n", message, target_name);
    
    return 0;
}


int read_line(int fd, char* buffer, int max_size)
{
    int i = 0;
    char c;
    
    while(i < max_size - 1){
        int n_read = read(fd, &c, 1);
        if(n_read <= 0){
            if(i == 0){
                LOG("read_line: Error or EOF on first read, n_read=%d\n", n_read);
                return usual_read_errors(n_read);
            }
            LOG("read_line: EOF or error after reading %d chars\n", i);
            break;  // EOF or error, but we have some data
        }
        
        if(c == '\n'){
            LOG("read_line: Found newline after %d chars\n", i);
            break;
        }
        
        buffer[i++] = c;
    }
    
    buffer[i] = '\0';
    LOG("read_line: Read line: '%s' (length: %d)\n", buffer, i);
    return 0;
}


int handle_request()
{
    char line[IN_BUFFER_MAX_SIZE];
    int err;
    
    
    err = read_line(g_request_fd, line, IN_BUFFER_MAX_SIZE);
    if(err){
        LOG("handle_request: Error reading line: %d\n", err);
        return err;
    }
    
    
    if(strncmp(line, "choose_target", 13) == 0){
        LOG("handle_request: Detected choose_target command\n");
        return handle_choose_target(line);
    } else if(strncmp(line, "send_message", 12) == 0){
        LOG("handle_request: Detected send_message command\n");
        return handle_send_message(line);
    } else {
        LOG("handle_request: Unknown command: '%s'\n", line);
        return ERR_INVALID_COMMAND;
    }
}


void loop() 
{
    LOG("loop: Entering main loop\n");
    int iteration = 0;
    
    while(1){
        iteration++;
        
        int err = handle_request();
        if(err){
            usleep(200000);
        }
    }
}


void cleanup()
{
    close_fifo(g_request_fd);
    close_fifo(g_to_a_fd);
    close_fifo(g_to_b_fd);
}


int main(int argc, char *argv[])
{
    // Disable buffering for immediate output
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    
    // Force immediate output
    fprintf(stdout, "Router main() called\n");
    fprintf(stderr, "Router main() called (stderr)\n");
    fflush(stdout);
    fflush(stderr);

    LOG("Router starting...\n");
    LOG("Arguments: argc=%d\n", argc);
    for(int i=0; i<argc; ++i){
        LOG("  argv[%d] = %s\n", i, argv[i]);
    }

    g_request_fd = -1;
    g_to_a_fd = -1;
    g_to_b_fd = -1;
    g_current_target = TARGET_A;  // Default to A

    if(argc != 4) {
        LOG("Usage: %s [request_fifo] [to_a_fifo] [to_b_fifo]\n", argv[0]);
        LOG("Error: Expected 4 arguments, got %d\n", argc);
        return 1;
    }

    // Check path lengths
    LOG("Checking path lengths...\n");
    for(int i=1; i<4; ++i){
        int len = strlen(argv[i]);
        LOG("  Path %d: '%s' (length: %d)\n", i, argv[i], len);
        if(len >= PATH_MAX_LEN){
            LOG("Error: File path too long: %s (length: %d, max: %d)\n", argv[i], len, PATH_MAX_LEN);
            return 1;
        }
    }

    // Create request FIFO (may already exist from Python)
    int err = create_fifo(argv[1]);
    if(err){
        LOG("Failed to create request FIFO\n");
        return 2;
    }
    LOG("Request FIFO ready: %s\n", argv[1]);

    // Open request FIFO for reading (non-blocking initially, then we'll make it blocking)
    LOG("Opening request FIFO for reading: %s\n", argv[1]);
    g_request_fd = open(argv[1], O_RDONLY | O_NONBLOCK);
    if(g_request_fd == -1){
        LOG("Error: Could not open request fifo %s (errno: %d)\n", argv[1], errno);
        return 2;
    }
    LOG("Request FIFO opened successfully, fd=%d\n", g_request_fd);
    
    // Make it blocking for normal operation
    int flags = fcntl(g_request_fd, F_GETFL, 0);
    if(flags == -1){
        LOG("Warning: Could not get flags for request FIFO\n");
    } else {
        LOG("Request FIFO flags before: %d\n", flags);
        fcntl(g_request_fd, F_SETFL, flags & ~O_NONBLOCK);
        flags = fcntl(g_request_fd, F_GETFL, 0);
        LOG("Request FIFO flags after: %d (blocking mode)\n", flags);
    }
    LOG("Request FIFO ready for blocking reads\n");

    // Create FIFOs to processes A and B
    err = create_fifo(argv[2]);
    if(err){
        LOG("Failed to create FIFO to A: %s\n", argv[2]);
        cleanup();
        return 2;
    }
    LOG("Created FIFO to A: %s\n", argv[2]);
    
    err = create_fifo(argv[3]);
    if(err){
        LOG("Failed to create FIFO to B: %s\n", argv[3]);
        cleanup();
        return 2;
    }
    LOG("Created FIFO to B: %s\n", argv[3]);

    LOG("FIFOs created, waiting for processes A and B to connect...\n");

    // Open FIFOs to processes A and B for writing (this will block until readers open them)
    LOG("Attempting to open FIFO to A for writing: %s (this will block until process A opens it for reading)\n", argv[2]);
    g_to_a_fd = open(argv[2], O_WRONLY);
    if(g_to_a_fd == -1){
        LOG("Error: Could not open fifo to A %s (errno: %d)\n", argv[2], errno);
        cleanup();
        return 2;
    }
    LOG("Success: Process A connected, fd=%d\n", g_to_a_fd);

    LOG("Attempting to open FIFO to B for writing: %s (this will block until process B opens it for reading)\n", argv[3]);
    g_to_b_fd = open(argv[3], O_WRONLY);
    if(g_to_b_fd == -1){
        LOG("Error: Could not open fifo to B %s (errno: %d)\n", argv[3], errno);
        cleanup();
        return 2;
    }
    LOG("Success: Process B connected, fd=%d\n", g_to_b_fd);

    LOG("Router fully initialized!\n");
    LOG("  Request FIFO fd: %d\n", g_request_fd);
    LOG("  Process A FIFO fd: %d\n", g_to_a_fd);
    LOG("  Process B FIFO fd: %d\n", g_to_b_fd);
    LOG("  Default target: %s\n", g_current_target == TARGET_A ? "A" : "B");
    LOG("Router entering main loop...\n");
    
    loop();

    LOG("Router exiting, cleaning up...\n");
    cleanup();
    LOG("Router cleanup complete\n");

    return 0;
}

