#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/epoll.h>
#include <errno.h>

#include "common.h"

#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512

static int g_in_fds[3];      // FIFOs to receive requests from user1, user2 and admin
static int g_out_fds[3];     // FIFOs to send responses to user1, user2 and admin

static int g_auth[3];        // authentication state for each user
static int g_router_to_auth_fd = -1;   // FIFO to send auth requests to auth process
static int g_auth_to_router_fd = -1;   // FIFO to receive responses from auth process
static int g_access_req_fd = -1; // FIFO to send access requests to access process
static int g_access_resp_fd = -1; // FIFO to receive access responses from access process

int read_line_fd(int fd, char* buffer, int max_size)
{
    int i = 0;
    char c;
    while(i < max_size - 1){
        int n_read = read(fd, &c, 1);
        if(n_read <= 0){
            if(i == 0){
                return usual_read_errors(n_read);
            }
            break;
        }
        if(c == '\n') break;
        buffer[i++] = c;
    }
    buffer[i] = '\0';
    return 0;
}

void respond(int user_idx, const char* message)
{
    int len = strlen(message);
    // write plain line back to user (message + newline)
    write(g_out_fds[user_idx], message, len);
    write(g_out_fds[user_idx], "\n", 1);
}


void handle_auth(int user_idx, const char* line)
{
    // Expect: AUTH <password>
    char pass[256];
    int n = sscanf(line+4, "%255s", pass);
    if(n < 1){
        LOG("Malformed AUTH command from user %d: %s\n", user_idx+1, line);
        respond(user_idx, "AUTH_ERR_BAD_FORMAT");
        return;
    }

    // send request to auth process via fifo
    if(g_router_to_auth_fd < 0){
        LOG("No auth fifo available\n");
        respond(user_idx, "AUTH_ERR_NO_AUTH_PROCESS");
        return;
    }

    char buf[IN_BUFFER_MAX_SIZE];
    snprintf(buf, sizeof(buf), "%d %s\n", user_idx+1, pass);
    write(g_router_to_auth_fd, buf, strlen(buf));
    LOG("Sent auth request for uid=%d to auth process\n", user_idx);

    // give auth process a moment to write tto the fifo
    usleep(200000);

    char resp[IN_BUFFER_MAX_SIZE];
    int r = read_line_fd(g_auth_to_router_fd, resp, IN_BUFFER_MAX_SIZE);
    if(r != 0){
        LOG("Error reading auth response\n");
        respond(user_idx, "AUTH_NO_RESPONSE");
        return;
    }

    if (strncmp(resp, "AUTH_OK", 1) == 0) {
        respond(user_idx, "AUTH_OK");
        g_auth[user_idx] = 1;
    } else {
        respond(user_idx, "AUTH_ERROR");
    }
}


void handle_read(int user_idx, const char* line)
{
    if (g_auth[user_idx] == 0) {
        LOG("Operation failed: not authenticated\n");
        respond(user_idx, "READ_ERR_NOT_AUTH");
        return;
    }

    const char* path = line + 5;
    // forward request to access process: send "<uid> <path>\n"
    char uid_s[16];
    snprintf(uid_s, sizeof(uid_s), "%d", user_idx+1);
    if(g_access_req_fd < 0){
        LOG("No access fifo available\n");
        respond(user_idx, "READ_ERR_NO_ACCESS_PROCESS");
    }
    char req[IN_BUFFER_MAX_SIZE];
    snprintf(req, sizeof(req), "%s READ %s\n", uid_s, path);
    write(g_access_req_fd, req, strlen(req));
    LOG("Sent access request for uid=%s path=%s to access process\n", uid_s, path);

    // read response from access process (blocking read of a line)
    char resp[IN_BUFFER_MAX_SIZE];
    int r = read_line_fd(g_access_resp_fd, resp, IN_BUFFER_MAX_SIZE);
    if(r != 0){
        LOG("Error reading access response\n");
        respond(user_idx, "READ_ERR_NO_RESPONSE");
        return;
    }

    // If response starts with READ_CONTENT <n>, read n bytes next
    if(strncmp(resp, "READ_CONTENT ", 13) == 0){
        size_t nbytes = (size_t) atol(resp + 13);
        // read nbytes
        char *buf = malloc(nbytes + 1);
        size_t got = 0;
        while(got < nbytes){
            int m = read(g_access_resp_fd, buf + got, nbytes - got);
            if(m <= 0) break;
            got += m;
        }
        buf[got] = '\0';
        /* consume the trailing newline that access wrote after the content */
        char tr;
        int rr = read(g_access_resp_fd, &tr, 1);
        size_t preview = got < 64 ? got : 64;
        if(preview > 0){
            char h[3*65];
            int hp = 0;
            for(size_t i=0;i<preview;i++) hp += snprintf(h+hp, sizeof(h)-hp, "%02x ", (unsigned char)buf[i]);
        }
        /* forward content to user: send header then content */
        char hdr[128];
        snprintf(hdr, sizeof(hdr), "ACCESS_OK %s %zu\n", path, got);
        write(g_out_fds[user_idx], hdr, strlen(hdr));
        if(got > 0) {
            write(g_out_fds[user_idx], buf, got);
        }
        write(g_out_fds[user_idx], "\n", 1);
        free(buf);
    } else {
        // forward the line response (e.g., ACCESS_DENIED or ACCESS_ERR_NOFILE)
        write(g_out_fds[user_idx], resp, strlen(resp));
        write(g_out_fds[user_idx], "\n", 1);
    }
}


void handle_write(int user_idx, const char* line)
{
    if (g_auth[user_idx] == 0) {
        LOG("Operation failed: not authenticated\n");
        respond(user_idx, "WRITE_ERR_NOT_AUTH");
        return;
    }

    // format: WRITE <path> <content...>
    const char* rest = line + 6;
    // split path and content
    const char* sp = strchr(rest, ' ');
    if(!sp){
        respond(user_idx, "WRITE_ERR_BAD_FORMAT");
        return;
    }

    int path_len = sp - rest;
    char path[IN_BUFFER_MAX_SIZE];
    if(path_len >= (int)sizeof(path)){
        respond(user_idx, "WRITE_ERR_PATH_TOO_LONG");
        return;
    }

    memcpy(path, rest, path_len);
    path[path_len] = '\0';
    const char* content = sp + 1;

    char uid_s[16];
    snprintf(uid_s, sizeof(uid_s), "%d", user_idx+1);
    if(g_access_req_fd < 0){
        LOG("No access fifo available\n");
        respond(user_idx, "WRITE_ERR_NO_ACCESS_PROCESS");
    }
        
    char req[IN_BUFFER_MAX_SIZE];
    snprintf(req, sizeof(req), "%s WRITE %s %s\n", uid_s, path, content);
    write(g_access_req_fd, req, strlen(req));
    LOG("Sent write request for uid=%s path=%s to access process\n", uid_s, path);

    char resp[IN_BUFFER_MAX_SIZE];
    int r = read_line_fd(g_access_resp_fd, resp, IN_BUFFER_MAX_SIZE);
    if(r != 0){
        LOG("Error reading write response\n");
        respond(user_idx, "WRITE_ERR_NO_RESPONSE");
        return;
    }
    // forward response line to user
    write(g_out_fds[user_idx], resp, strlen(resp));
    write(g_out_fds[user_idx], "\n", 1);
}


void handle_command(int user_idx, const char* line)
{
    if(strncmp(line, "AUTH", 4) == 0){
        handle_auth(user_idx, line);
    } else if(strncmp(line, "READ ", 5) == 0){
        handle_read(user_idx, line);
    } else if(strncmp(line, "WRITE ", 6) == 0){
        handle_write(user_idx, line);
    } else {
        LOG("Unknown command from user %d: %s\n", user_idx+1, line);
        respond(user_idx, "ERR_UNKNOWN_CMD");
    }
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if(argc != 11){
        LOG("Usage: %s [fifo_u1_to_router] [fifo_u2_to_router] [fifo_admin_to_router] [fifo_router_to_u1] [fifo_router_to_u2] [fifo_router_to_admin] [fifo_router_to_auth] [fifo_auth_to_router] [fifo_router_to_access] [fifo_access_to_router]\n", argv[0]);
        return 1;
    }

    for(int i=1;i<=8;++i){
        if(strlen(argv[i]) >= PATH_MAX_LEN){
            LOG("File path too long: %s\n", argv[i]);
            return 1;
        }
    }

    // create FIFOs
    create_fifo(argv[1]);
    create_fifo(argv[2]);
    create_fifo(argv[3]);
    create_fifo(argv[4]);
    create_fifo(argv[5]); // router->auth fifo
    create_fifo(argv[6]);
    create_fifo(argv[7]); // router->access fifo
    create_fifo(argv[8]); // access->router fifo
    create_fifo(argv[9]); // access->router fifo
    create_fifo(argv[10]); // access->router fifo

    
    // open out fifos for writing (blocks until users open read end)
    g_out_fds[0] = open(argv[4], O_WRONLY);
    g_out_fds[1] = open(argv[5], O_WRONLY);
    g_out_fds[2] = open(argv[6], O_WRONLY);
    
    // open auth fifo for writing
    g_router_to_auth_fd = open(argv[7], O_WRONLY);
    g_auth_to_router_fd = open(argv[8], O_RDONLY);

    // open in fifos for reading non-blocking
    g_in_fds[0] = open(argv[1], O_RDONLY);
    g_in_fds[1] = open(argv[2], O_RDONLY);
    g_in_fds[2] = open(argv[3], O_RDONLY);
    for(int i=0;i<3;++i){
        int flags = fcntl(g_in_fds[i], F_GETFL, 0);
        fcntl(g_in_fds[i], F_SETFL, flags | O_NONBLOCK);
    }

    g_auth[0] = 0;
    g_auth[1] = 0;
    g_auth[2] = 0;

    // open access request/response FIFOs
    g_access_req_fd = open(argv[9], O_WRONLY);
    g_access_resp_fd = open(argv[10], O_RDONLY);

    LOG("Router started\n");

    char line[IN_BUFFER_MAX_SIZE];

    int ep = make_epoll(g_in_fds, 3);
    if (ep < 0) {
        LOG("Issue when creating epoll");
        return 1;
    }

    while(1){
        struct epoll_event events[8];
        int n = epoll_wait(ep, events, 8, -1);
        if (n < 0) {
            if (errno == EINTR) continue;
            LOG("Error on epoll wait");
            break;
        }
        for(int i=0; i<n; ++i){
            int idx = events[i].data.u32;
            int fd  = g_in_fds[idx];

            if (events[i].events & EPOLLIN) {
                int err = read_line_fd(fd, line, IN_BUFFER_MAX_SIZE);
                if(err == 0){
                    if(strlen(line) > 0){
                        LOG("Received from user %d: %s\n", idx+1, line);
                        handle_command(idx, line);
                    }
                }
            }
        }
    }

    return 0;
}
