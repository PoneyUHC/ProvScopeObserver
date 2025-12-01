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

static int g_in_fds[2];      // FIFOs to receive requests from user1 and user2
static int g_out_fds[2];     // FIFOs to send responses to user1 and user2

static int g_auth[2];        // authentication state for each user
static int g_auth_fd = -1;   // FIFO to send auth requests to auth process
static char g_allow_file[PATH_MAX_LEN];
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

void handle_command(int user_idx, const char* line)
{
    if(strncmp(line, "AUTH", 4) == 0){
        // Expect: AUTH <uid> <password>
        char uid_s[64];
        char pass[256];
        int n = sscanf(line+4, "%63s %255s", uid_s, pass);
        if(n < 2){
            LOG("Malformed AUTH command from user %d: %s\n", user_idx+1, line);
            respond(user_idx, "AUTH_ERR_BAD_FORMAT");
            return;
        }

        // send request to auth process via fifo
        if(g_auth_fd != -1){
            char buf[IN_BUFFER_MAX_SIZE];
            snprintf(buf, sizeof(buf), "%s %s\n", uid_s, pass);
            write(g_auth_fd, buf, strlen(buf));
            LOG("Sent auth request for uid=%s to auth process\n", uid_s);

            // give auth process a moment to write the allow file
            usleep(200000);

            // read allow file and set g_auth for this uid
            FILE *af = fopen(g_allow_file, "r");
            if(af){
                char linebuf[256];
                int last_val = -1;
                while(fgets(linebuf, sizeof(linebuf), af)){
                    // look for pattern [uid] = X
                    char key[64]; int val;
                    if(sscanf(linebuf, "[%63[^]]] = %d", key, &val) == 2){
                        if(strcmp(key, uid_s) == 0){
                            last_val = val;
                        }
                    }
                }
                fclose(af);
                if(last_val != -1){
                    int idx = atoi(uid_s) - 1; // map uid 1->index0, 2->index1
                    if(idx >= 0 && idx < 2){
                        g_auth[idx] = last_val;
                        LOG("Auth state for uid=%s set to %d\n", uid_s, last_val);
                    }
                }
            } else {
                LOG("Could not open allow file %s to read result\n", g_allow_file);
            }

            respond(user_idx, "AUTH_REQUEST_SENT");
        } else {
            LOG("No auth fifo available\n");
            respond(user_idx, "AUTH_ERR_NO_AUTH_PROCESS");
        }

        return;
    }

    if(strncmp(line, "ACCESS ", 7) == 0){
        const char* path = line + 7;
        // forward request to access process: send "<uid> <path>\n"
        char uid_s[16];
        snprintf(uid_s, sizeof(uid_s), "%d", user_idx+1);
        if(g_access_req_fd != -1){
            char req[IN_BUFFER_MAX_SIZE];
            snprintf(req, sizeof(req), "%s READ %s\n", uid_s, path);
            write(g_access_req_fd, req, strlen(req));
            LOG("Sent access request for uid=%s path=%s to access process\n", uid_s, path);

            // read response from access process (blocking read of a line)
            char resp[IN_BUFFER_MAX_SIZE];
            int r = read_line_fd(g_access_resp_fd, resp, IN_BUFFER_MAX_SIZE);
            if(r != 0){
                LOG("Error reading access response\n");
                respond(user_idx, "ACCESS_ERR_NO_RESPONSE");
                return;
            }

            // If response starts with ACCESS_CONTENT <n>, read n bytes next
            if(strncmp(resp, "ACCESS_CONTENT ", 15) == 0){
                size_t nbytes = (size_t) atol(resp + 15);
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
        } else {
            LOG("No access fifo available\n");
            respond(user_idx, "ACCESS_ERR_NO_ACCESS_PROCESS");
        }
        return;
    }

    if(strncmp(line, "WRITE ", 6) == 0){
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
        if(g_access_req_fd != -1){
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
        } else {
            LOG("No access fifo available\n");
            respond(user_idx, "WRITE_ERR_NO_ACCESS_PROCESS");
        }
        return;
    }

    LOG("Unknown command from user %d: %s\n", user_idx+1, line);
    respond(user_idx, "ERR_UNKNOWN_CMD");
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if(argc != 9){
        LOG("Usage: %s [fifo_u1_to_router] [fifo_u2_to_router] [fifo_router_to_u1] [fifo_router_to_u2] [fifo_router_to_auth] [allow_file] [fifo_router_to_access] [fifo_access_to_router]\n", argv[0]);
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
    create_fifo(argv[7]); // router->access fifo
    create_fifo(argv[8]); // access->router fifo

    // open out fifos for writing (blocks until users open read end)
    g_out_fds[0] = open(argv[3], O_WRONLY);
    g_out_fds[1] = open(argv[4], O_WRONLY);

    // open auth fifo for writing
    g_auth_fd = open(argv[5], O_WRONLY);

    // open in fifos for reading non-blocking
    g_in_fds[0] = open(argv[1], O_RDONLY);
    g_in_fds[1] = open(argv[2], O_RDONLY);
    for(int i=0;i<2;++i){
        int flags = fcntl(g_in_fds[i], F_GETFL, 0);
        fcntl(g_in_fds[i], F_SETFL, flags | O_NONBLOCK);
    }

    g_auth[0] = 0;
    g_auth[1] = 0;

    // store allow file path
    strncpy(g_allow_file, argv[6], PATH_MAX_LEN-1);
    g_allow_file[PATH_MAX_LEN-1] = '\0';

    // open access request/response FIFOs
    g_access_req_fd = open(argv[7], O_WRONLY);
    g_access_resp_fd = open(argv[8], O_RDONLY);

    LOG("Router (users) started\n");

    char line[IN_BUFFER_MAX_SIZE];

    while(1){
        for(int u=0; u<2; ++u){
            int err = read_line_fd(g_in_fds[u], line, IN_BUFFER_MAX_SIZE);
            if(err == 0){
                if(strlen(line) > 0){
                    LOG("Received from user %d: %s\n", u+1, line);
                    handle_command(u, line);
                }
            }
            // else nothing to read or error
        }
        usleep(100000);
    }

    return 0;
}
