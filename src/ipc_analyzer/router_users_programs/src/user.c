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

int read_n_bytes(int fd, void* buf, int n)
{
    int got = 0;
    while(got < n){
        int r = read(fd, ((char*)buf)+got, n-got);
        if(r <= 0) return r;
        got += r;
    }
    return got;
}

int read_line_fd(int fd, char* buffer, int max_size)
{
    int i = 0;
    char c;
    while(i < max_size - 1){
        int n_read = read(fd, &c, 1);
        if(n_read <= 0){
            if(i == 0) return usual_read_errors(n_read);
            break;
        }
        if(c == '\n') break;
        buffer[i++] = c;
    }
    buffer[i] = '\0';
    return 0;
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    LOG("User program started\n");
    if(argc < 4){
        LOG("Usage: %s [fifo_to_router] [fifo_from_router] [fifo_commands]\n", argv[0]);
        return 1;
    }

    if(strlen(argv[1]) >= PATH_MAX_LEN || strlen(argv[2]) >= PATH_MAX_LEN){
        LOG("Path too long\n");
        return 1;
    }

    char* fifo_to = argv[1];
    char* fifo_from = argv[2];

     /* open read end blocking: retrying reads on EAGAIN produced errors
         in earlier runs. Blocking open ensures the FIFO read end is ready
         and subsequent read() calls will block until data arrives. */
     int in_fd = open(fifo_from, O_RDONLY);
    if(in_fd == -1){
        LOG("Could not open fifo from router: %s\n", fifo_from);
        return 2;
    }

    int out_fd = open(fifo_to, O_WRONLY);
    if(out_fd == -1){
        LOG("Could not open fifo to router: %s\n", fifo_to);
        return 2;
    }

    /* Open commands FIFO (blocking). The program will read commands from this FIFO
       and forward them to the router as if the user typed them. If the writer on the
       commands FIFO closes, we re-open it to wait for new writers. */
    const char* fifo_cmds = argv[3];
    int cmd_fd = open(fifo_cmds, O_RDONLY);
    if(cmd_fd == -1){
        LOG("Could not open fifo commands: %s\n", fifo_cmds);
        return 2;
    }

    while(1){
        char cmdbuf[IN_BUFFER_MAX_SIZE];
        int r = read_line_fd(cmd_fd, cmdbuf, sizeof(cmdbuf));
        if(r == 0){
            // Got a command line (without trailing newline). Send to router.
            char sendbuf[IN_BUFFER_MAX_SIZE];
            snprintf(sendbuf, sizeof(sendbuf), "%s\n", cmdbuf);
            ssize_t w = write(out_fd, sendbuf, strlen(sendbuf));
            if(w < 0){
                LOG("Failed to write to router FIFO\n");
            } else {
                LOG("Forwarded command: %s\n", cmdbuf);
            }

            // wait for response line from router
            char resp[IN_BUFFER_MAX_SIZE];
            int rr = read_line_fd(in_fd, resp, sizeof(resp));
            if(rr == 0){
                if(strncmp(resp, "ACCESS_OK ", 10) == 0 || strncmp(resp, "ACCESS_CONTENT ", 15) == 0){
                    size_t size = 0;
                    char pathbuf[256];
                    if(sscanf(resp, "ACCESS_OK %255s %zu", pathbuf, &size) < 1){
                        sscanf(resp, "ACCESS_CONTENT %zu", &size);
                    }

                    if(size > 0){
                        char *buf = malloc(size + 1);
                        int got = read_n_bytes(in_fd, buf, size);
                        if(got > 0){
                            buf[got] = '\0';
                            LOG("Got response (content, %d bytes): %s\n", got, buf);
                        } else {
                            LOG("Got response header but could not read content\n");
                        }
                        free(buf);
                        // consume trailing newline
                        char nl;
                        read(in_fd, &nl, 1);
                    } else {
                        LOG("Got response: %s\n", resp);
                    }
                } else {
                    LOG("Got response: %s\n", resp);
                }
            } else {
                LOG("No response received\n");
            }
        } else {
            // handle EOF or read error: usual_read_errors already logs; on EOF reopen cmd fifo
            if(r == ERR_NOTHING_TO_READ){
                // writer closed; reopen to wait for new writer
                close_fifo(cmd_fd);
                cmd_fd = open(fifo_cmds, O_RDONLY);
                if(cmd_fd == -1){
                    LOG("Could not re-open fifo commands: %s\n", fifo_cmds);
                    break;
                }
                continue;
            } else {
                LOG("Error reading commands FIFO\n");
                break;
            }
        }
    }

    close_fifo(cmd_fd);
    close_fifo(in_fd);
    close_fifo(out_fd);

    return 0;
}
