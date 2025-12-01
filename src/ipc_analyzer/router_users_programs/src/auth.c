#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#include "common.h"

#define PATH_MAX_LEN 256
#define IN_BUFFER_MAX_SIZE 512

static int g_in_fd = -1;

static int read_line_fd(int fd, char* buffer, int max_size)
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

static int parse_auth_request(const char *line, char *uid_out, size_t uid_sz, char *pass_out, size_t pass_sz)
{
    int n = sscanf(line, "%63s %255s", uid_out, pass_out);
    return (n == 2) ? 0 : -1;
}

static int read_expected_password(const char *password_file, const char *uid, char *out, size_t sz)
{
    FILE *pf = fopen(password_file, "r");
    if(!pf) return -1;
    char line[512];
    while(fgets(line, sizeof(line), pf)){
        size_t len = strlen(line);
        if(len > 0 && line[len-1] == '\n') line[len-1] = '\0';
        char *p = line;
        // skip leading whitespace
        while(*p && isspace((unsigned char)*p)) p++;
        if(*p == '\0' || *p == '#') continue;
        size_t uidlen = strlen(uid);
        if(strncmp(p, uid, uidlen) == 0){
            char sep = p[uidlen];
            if(sep == ':' || sep == '=' || isspace((unsigned char)sep)){
                char *pw = p + uidlen;
                if(*pw == ':' || *pw == '=') pw++;
                while(*pw && isspace((unsigned char)*pw)) pw++;
                strncpy(out, pw, sz-1);
                out[sz-1] = '\0';
                fclose(pf);
                return 0;
            }
        }
    }
    fclose(pf);
    return -1;
}

static int write_allow_entry(const char *allow_file, const char *uid, int ok)
{
    FILE *af = fopen(allow_file, "a");
    if(!af) return -1;
    fprintf(af, "[%s] = %d\n", uid, ok);
    fclose(af);
    return 0;
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if(argc != 4){
        LOG("Usage: %s [fifo_in] [password_file] [allow_file]\n", argv[0]);
        return 1;
    }

    const char* fifo_in = argv[1];
    const char* password_file = argv[2];
    const char* allow_file = argv[3];

    if(strlen(fifo_in) >= PATH_MAX_LEN || strlen(password_file) >= PATH_MAX_LEN || strlen(allow_file) >= PATH_MAX_LEN){
        LOG("Path too long\n");
        return 1;
    }

    create_fifo((char*)fifo_in);

    g_in_fd = open_fifo_rd(fifo_in, 0);
    if(g_in_fd == -1){
        LOG("Could not open fifo %s\n", fifo_in);
        return 2;
    }

    LOG("Auth process started, monitoring %s, password file=%s, allow=%s\n", fifo_in, password_file, allow_file);

    char line[IN_BUFFER_MAX_SIZE];
    char uid_s[64];
    char pass[256];
    char expected[256];

    while(1){
        int err = read_line_fd(g_in_fd, line, IN_BUFFER_MAX_SIZE);
        if(err == 0){
            if(strlen(line) == 0) continue;
            LOG("Auth request: %s\n", line);

            if(parse_auth_request(line, uid_s, sizeof(uid_s), pass, sizeof(pass)) != 0){
                LOG("Malformed auth request: %s\n", line);
                continue;
            }

            if(read_expected_password(password_file, uid_s, expected, sizeof(expected)) != 0){
                LOG("Could not find password for uid=%s in %s\n", uid_s, password_file);
                continue;
            }

            int ok = (strcmp(pass, expected) == 0) ? 1 : 0;
            if(write_allow_entry(allow_file, uid_s, ok) != 0){
                LOG("Could not open allow file %s\n", allow_file);
                continue;
            }

            LOG("Auth result for uid=%s -> %d\n", uid_s, ok);
        } else {
            struct timespec ts = {0, 100000000}; /* 100ms */
            nanosleep(&ts, NULL);
        }
    }

    return 0;
}
