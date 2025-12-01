#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"

#define PATH_MAX_LEN 512
#define IN_BUFFER_MAX_SIZE 8192

static int g_in_fd = -1;   // router -> access
static int g_out_fd = -1;  // access -> router
static char g_allow_file[PATH_MAX_LEN];

/*
 * access.c
 *
 * Service that receives requests from router over a FIFO, checks the
 * allow file and either returns file contents or writes files on behalf
 * of users.
 */

#include <errno.h>
#include <stdarg.h>

static int read_line_fd(int fd, char* buffer, int max_size)
{
    int i = 0;
    char c;

    while (i < max_size - 1) {
        int n_read = read(fd, &c, 1);
        if (n_read <= 0) {
            if (i == 0) return usual_read_errors(n_read);
            break;
        }
        if (c == '\n') break;
        buffer[i++] = c;
    }

    buffer[i] = '\0';
    return 0;
}

static ssize_t write_all(int fd, const void* buf, size_t len)
{
    const char *p = (const char*)buf;
    size_t written = 0;

    while (written < len) {
        ssize_t w = write(fd, p + written, len - written);
        if (w <= 0) return w;
        written += (size_t)w;
    }
    return (ssize_t)written;
}

/* Check allow file for a given uid string. Returns 1 if allowed, 0 otherwise. */
static int user_allowed(const char* uid_s)
{
    FILE *af = fopen(g_allow_file, "r");
    if (!af) return 0;

    char line[512];
    int last_val = 0;

    while (fgets(line, sizeof(line), af)) {
        char key[64]; int val;
        /* tolerate a few spacing variants */
        if (sscanf(line, "[%63[^]]]= %d", key, &val) == 2 ||
            sscanf(line, "[%63[^]] ] = %d", key, &val) == 2 ||
            sscanf(line, "[%63[^]] ]=%d", key, &val) == 2) {
            if (strcmp(key, uid_s) == 0) last_val = val;
        }
    }

    fclose(af);
    return last_val;
}

/* Read entire file into buffer. Caller must free *out_buf. On success
 * returns 0 and sets *out_buf and *out_size. On error returns -1. */
static int read_file_content(const char *path, char **out_buf, size_t *out_size)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;

    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    long sz = ftell(f);
    if (sz < 0) { fclose(f); return -1; }
    rewind(f);

    char *buf = malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return -1; }

    size_t read_total = fread(buf, 1, (size_t)sz, f);
    fclose(f);

    buf[read_total] = '\0';
    *out_buf = buf;
    *out_size = read_total;
    return 0;
}

/* Helpers to send standardized responses back to router. */
static void send_line_response(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    write_all(g_out_fd, buf, strlen(buf));
}

static void send_access_content(const char *data, size_t size)
{
    char hdr[64];
    snprintf(hdr, sizeof(hdr), "ACCESS_CONTENT %zu\n", size);
    write_all(g_out_fd, hdr, strlen(hdr));
    if (size > 0) write_all(g_out_fd, data, size);
    write_all(g_out_fd, "\n", 1);
}

static void handle_read_request(const char *uid, const char *rest)
{
    const char *path = rest;

    if (!user_allowed(uid)) {
        send_line_response("ACCESS_DENIED %s\n", path);
        LOG("Access denied for uid=%s to %s\n", uid, path);
        return;
    }

    char *content = NULL;
    size_t size = 0;
    if (read_file_content(path, &content, &size) != 0) {
        send_line_response("ACCESS_ERR_NOFILE %s\n", path);
        LOG("File not found: %s\n", path);
        return;
    }

    send_access_content(content, size);
    LOG("Sent %zu bytes of %s to router for uid=%s\n", size, path, uid);
    free(content);
}

static void handle_write_request(const char *uid, const char *rest)
{
    /* rest is expected to be: "<path> <content...>" */
    char tmp[PATH_MAX_LEN + 1];
    strncpy(tmp, rest, sizeof(tmp)-1);
    tmp[sizeof(tmp)-1] = '\0';

    char *sp = strchr(tmp, ' ');
    if (!sp) {
        send_line_response("WRITE_ERR_BAD_FORMAT\n");
        LOG("Malformed WRITE rest: %s\n", rest);
        return;
    }

    *sp = '\0';
    const char *path = tmp;
    const char *content = sp + 1;

    if (!user_allowed(uid)) {
        send_line_response("ACCESS_DENIED %s\n", path);
        LOG("Write denied for uid=%s to %s\n", uid, path);
        return;
    }

    FILE *f = fopen(path, "wb");
    if (!f) {
        send_line_response("WRITE_ERR_NOFILE %s\n", path);
        LOG("Could not open file for writing: %s\n", path);
        return;
    }

    size_t written = fwrite(content, 1, strlen(content), f);
    fclose(f);

    send_line_response("WRITE_OK %s\n", path);
    LOG("Wrote %zu bytes to %s for uid=%s\n", written, path, uid);
}

int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if (argc != 4) {
        LOG("Usage: %s [fifo_router_to_access] [fifo_access_to_router] [allow_file]\n", argv[0]);
        return 1;
    }

    const char *fifo_in = argv[1];
    const char *fifo_out = argv[2];
    strncpy(g_allow_file, argv[3], sizeof(g_allow_file)-1);
    g_allow_file[sizeof(g_allow_file)-1] = '\0';

    /* Ensure FIFOs exist, then open them */
    create_fifo((char*)fifo_in);
    create_fifo((char*)fifo_out);

    g_in_fd = open_fifo_rd(fifo_in, 0);
    if (g_in_fd < 0) { LOG("Could not open input fifo %s\n", fifo_in); return 1; }

    g_out_fd = open_fifo_wr(fifo_out);
    if (g_out_fd < 0) { LOG("Could not open output fifo %s\n", fifo_out); return 1; }

    char line[IN_BUFFER_MAX_SIZE];

    while (1) {
        int err = read_line_fd(g_in_fd, line, sizeof(line));
        if (err != 0) {
            usleep(100000);
            continue;
        }

        if (line[0] == '\0') continue;

        LOG("Access request: %s\n", line);

        /* parse: <uid> <OP> <rest> (rest may contain spaces) */
        char uid_s[64]; char op[32]; char rest[PATH_MAX_LEN];
        int n = sscanf(line, "%63s %31s %511[^\\n]", uid_s, op, rest);
        if (n < 2) {
            send_line_response("ACCESS_ERR_BAD_FORMAT\n");
            LOG("Malformed access request: %s\n", line);
            continue;
        }

        if (strcmp(op, "READ") == 0) {
            if (n < 3) { send_line_response("ACCESS_ERR_BAD_FORMAT\n"); LOG("Malformed READ request: %s\n", line); continue; }
            handle_read_request(uid_s, rest);
        } else if (strcmp(op, "WRITE") == 0) {
            if (n < 3) { send_line_response("WRITE_ERR_BAD_FORMAT\n"); LOG("Malformed WRITE request: %s\n", line); continue; }
            handle_write_request(uid_s, rest);
        } else {
            send_line_response("ACCESS_ERR_UNKNOWN_OP\n");
            LOG("Unknown op %s in access request\n", op);
        }
    }

    return 0;
}
