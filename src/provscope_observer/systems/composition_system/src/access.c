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

#define PATH_MAX_LEN 512
#define IN_BUFFER_MAX_SIZE 8192

static int g_in_fd = -1;   // router -> access
static int g_out_fd = -1;  // access -> router
static char g_allow_file[PATH_MAX_LEN];
static char g_policy_file[PATH_MAX_LEN];
static char g_root_dir[PATH_MAX_LEN];

/*
 * access.c
 *
 * Service that receives requests from router over a FIFO, checks the
 * allow file and either returns file contents or writes files on behalf
 * of users.
 */

#include <errno.h>
#include <stdarg.h>


int portable_dirname(const char *path, char out[PATH_MAX_LEN])
{
    size_t len;

    if (!path || !out)
        return -1;

    len = strlen(path);

    if (len == 0) {
        strcpy(out, ".");
        return 0;
    }

    /* Make a working copy because we'll modify it */
    if (len >= PATH_MAX_LEN)
        len = PATH_MAX_LEN - 1;

    memcpy(out, path, len);
    out[len] = '\0';

    /* Remove trailing slashes (except keep root "/") */
    while (len > 1 && out[len - 1] == '/') {
        out[len - 1] = '\0';
        len--;
    }

    /* Find last slash */
    char *slash = strrchr(out, '/');
    if (!slash) {
        /* No slash at all → dirname is "." */
        strcpy(out, ".");
        return 0;
    }

    /* If the slash is at the beginning, the directory is "/" */
    if (slash == out) {
        out[1] = '\0';  /* keep "/" */
        return 0;
    }

    /* Cut at the slash → terminate the directory part */
    *(slash+1) = '\0';

    return 0;
}


static void trim_line(char *s)
{
    size_t len;

    if (!s)
        return;

    len = strlen(s);
    while (len > 0 && (s[len - 1] == '\n' || s[len - 1] == '\r' || s[len - 1] == ' ' || s[len - 1] == '\t')) {
        s[len - 1] = '\0';
        len--;
    }
}

/*
 * Check if 'path' is inside (or equal to) 'dir'.
 * We require either exact match, or dir is a prefix followed by '/'.
 * Example:
 *  dir = /home/user/secret
 *  path = /home/user/secret/foo.txt  -> forbidden
 *  path = /home/user/secret          -> forbidden
 *  path = /home/user/secret_stuff    -> allowed
 */
static int is_under_dir(const char *path, const char *dir)
{
    size_t dlen;

    if (!path || !dir)
        return 0;

    dlen = strlen(dir);
    if (dlen == 0)
        return 0;

    if (strncmp(path, dir, dlen) != 0)
        return 0;

    /* exact match */
    if (path[dlen] == '\0')
        return 1;

    /* dir is a prefix, require directory boundary */
    if (path[dlen] == '/')
        return 1;

    return 0;
}


int inplace_path_move(const char *uid, char path[PATH_MAX_LEN])
{
    size_t root_len, user_len, path_len, new_len;
    int slash_after_root = 0;
    int slash_after_user = 0;
    char user_component[PATH_MAX_LEN];

    if (!path || strcmp(g_root_dir, "") == 0)
        return -1;

    root_len = strlen(g_root_dir);
    path_len = strlen(path);

    if (uid) {
        /* Build user_uid */
        snprintf(user_component, sizeof(user_component), "user_%s", uid);
        user_len = strlen(user_component);
    }

    /* Need slash after root? */
    if (g_root_dir[root_len - 1] != '/')
        slash_after_root = 1;

    /* Need slash after user_uid? */
    if (path_len > 0 && path[0] != '/')
        slash_after_user = 1;

    /* Total new size */
    new_len =
        root_len +
        slash_after_root +
        path_len +
        1;

    if (uid) {
        new_len += user_len + slash_after_user;
    }


    if (new_len > PATH_MAX_LEN)
        return -1;
        
    /* Shift the original path right */
    if (uid) {
        memmove(
            path + root_len + slash_after_root + user_len + slash_after_user,
            path,
            path_len + 1
        );
    } else {
        memmove(
            path + root_len + slash_after_root,
            path,
            path_len + 1
        );
    }

    /* Copy root prefix */
    memcpy(path, g_root_dir, root_len);

    /* Slash after root */
    size_t offset = root_len;
    if (slash_after_root)
        path[offset++] = '/';

    if (uid) {
        /* Insert user_uid */
        memcpy(path + offset, user_component, user_len);
        offset += user_len;
    
        /* Slash after user_uid */
        if (slash_after_user)
            path[offset++] = '/';
    }

    /* original path already in place */

    return 0;
}


int check_access_allowed(const char *uid, char path[PATH_MAX_LEN]) 
{
    char dir[PATH_MAX_LEN];
    char resolved[PATH_MAX_LEN];
    FILE *fp;
    char line[PATH_MAX_LEN];
    int in_target_user_block = 0;
    int access_forbidden = 0;

    LOG("check_access_allowed: uid='%s', path='%s'\n", uid ? uid : "(null)", path ? path : "(null)");

    if (!uid || !path) {
        LOG("check_access_allowed: invalid input (uid or path is NULL) -> deny\n");
        return 0;   /* reject on invalid input */
    }

    if (portable_dirname(path, dir) != 0)
        return -1;

    if (!realpath(dir, resolved))
        return -1;

    int len = strlen(resolved);
    resolved[len] = '/';
    resolved[len+1] = '\0';

    LOG("check_access_allowed: resolved target directory to '%s'\n", resolved);

    fp = fopen(g_policy_file, "r");
    if (!fp) {
        LOG("check_access_allowed: could not open policy file '%s' -> allow\n",
            g_policy_file);
        return 1;   /* fail-open by policy */
    }

    LOG("check_access_allowed: opened policy file '%s'\n", g_policy_file);

    while (fgets(line, sizeof(line), fp) != NULL) {
        trim_line(line);

        if (line[0] == '\0')
            continue;

        if (strcmp(line, "USER") == 0) {
            LOG("check_access_allowed: found 'USER' marker\n");

            /* Next line should be the UID for this block */
            if (fgets(line, sizeof(line), fp) == NULL) {
                LOG("check_access_allowed: unexpected EOF after USER\n");
                break;
            }

            trim_line(line);
            LOG("check_access_allowed: user block uid='%s'\n", line);

            if (strcmp(line, uid) == 0) {
                LOG("check_access_allowed: UID matches, entering user block\n");
                in_target_user_block = 1;
            } else {
                LOG("check_access_allowed: UID does not match, skipping block\n");
                in_target_user_block = 0;
            }

            continue;
        }

        if (in_target_user_block) {

            inplace_path_move(NULL, line);
            
            LOG("check_access_allowed: checking forbidden dir='%s'\n", line);

            if (is_under_dir(resolved, line)) {
                LOG("check_access_allowed: MATCH -> access forbidden! (%s under %s)\n",
                    resolved, line);
                access_forbidden = 1;
                break;
            }
        }
    }

    fclose(fp);

    if (access_forbidden) {
        LOG("check_access_allowed: final decision: DENY\n");
        return 0;
    } else {
        LOG("check_access_allowed: final decision: ALLOW\n");
        return 1;
    }
}


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

// /* Check allow file for a given uid string. Returns 1 if allowed, 0 otherwise. */
// static int user_allowed(const char* uid)
// {
//     FILE *af = fopen(g_allow_file, "r");
//     if (!af) return 0;

//     char line[512];
//     int last_val = 0;

//     while (fgets(line, sizeof(line), af)) {
//         char key[64]; int val;
//         /* tolerate a few spacing variants */
//         if (sscanf(line, "[%63[^]]]= %d", key, &val) == 2 ||
//             sscanf(line, "[%63[^]] ] = %d", key, &val) == 2 ||
//             sscanf(line, "[%63[^]] ]=%d", key, &val) == 2) {
//             if (strcmp(key, uid) == 0) last_val = val;
//         }
//     }

//     fclose(af);
//     return last_val;
// }

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
    LOG("Sending message %s", buf);
    write_all(g_out_fd, buf, strlen(buf));
}

static void send_access_content(const char *data, size_t size)
{
    char hdr[64];
    snprintf(hdr, sizeof(hdr), "READ_CONTENT %zu\n", size);
    write_all(g_out_fd, hdr, strlen(hdr));
    if (size > 0) write_all(g_out_fd, data, size);
    write_all(g_out_fd, "\n", 1);
}

static void handle_read_request(const char *uid, char *rest)
{
    char *path = rest;
    int is_admin = strncmp(uid, "3", 1);

    if (!is_admin) {
        inplace_path_move(uid, path);
    
        int path_ok = check_access_allowed(uid, path);
        if (!path_ok) {
            send_line_response("ACCESS_ERR_NOT_ALLOWED\n");
            LOG("Access denied for uid=%s to %s\n", uid, path);
            return;
        }
    
    
        // if (!user_allowed(uid)) {
        //     send_line_response("ACCESS_DENIED %s\n", path);
        //     LOG("Access denied for uid=%s to %s\n", uid, path);
        //     return;
        // }
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
    char *path = tmp;
    const char *content = sp + 1;
    char content_cpy[IN_BUFFER_MAX_SIZE];
    strcpy(content_cpy, content);

    int is_admin = !strncmp(uid, "3", 1);

    if (!is_admin) {
        inplace_path_move(uid, path);

        int path_ok = check_access_allowed(uid, path);
        if (!path_ok) {
            send_line_response("ACCESS_ERR_NOT_ALLOWED\n");
            LOG("Access denied for uid=%s to %s\n", uid, path);
            return;
        }
    } else {
        inplace_path_move(NULL, path);
    }

    FILE *f = fopen(path, "wb");
    if (!f) {
        send_line_response("WRITE_ERR_NOFILE %s\n", path);
        LOG("Could not open file for writing: %s\n", path);
        return;
    }

    size_t written = fwrite(content_cpy, 1, strlen(content_cpy), f);
    fclose(f);

    send_line_response("WRITE_OK %s\n", path);
    LOG("Wrote %zu bytes to %s for uid=%s\n", written, path, uid);
}


void handle_request(char line[IN_BUFFER_MAX_SIZE])
{
    LOG("Access request: %s\n", line);

    /* parse: <uid> <OP> <rest> (rest may contain spaces) */
    char uid[64]; char op[32]; char rest[PATH_MAX_LEN];
    int n = sscanf(line, "%63s %31s %511[^\\n]", uid, op, rest);
    if (n < 2) {
        send_line_response("ACCESS_ERR_BAD_FORMAT\n");
        LOG("Malformed access request: %s\n", line);
        return;
    }

    if (strcmp(op, "READ") == 0) {
        if (n < 3) { 
            send_line_response("ACCESS_ERR_BAD_FORMAT\n"); 
            LOG("Malformed READ request: %s\n", line); 
            return; 
        }
        handle_read_request(uid, rest);
    } else if (strcmp(op, "WRITE") == 0) {
        if (n < 3) { 
            send_line_response("WRITE_ERR_BAD_FORMAT\n"); 
            LOG("Malformed WRITE request: %s\n", line); 
            return; 
        }
        handle_write_request(uid, rest);
    } else {
        send_line_response("ACCESS_ERR_UNKNOWN_OP\n");
        LOG("Unknown op %s in access request\n", op);
    }
}



int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if (argc != 6) {
        LOG("Usage: %s [fifo_router_to_access] [fifo_access_to_router] [allow_file] [policy_file] [root_dir]\n", argv[0]);
        return 1;
    }

    const char *fifo_in = argv[1];
    const char *fifo_out = argv[2];
    strncpy(g_allow_file, argv[3], sizeof(g_allow_file)-1);
    g_allow_file[sizeof(g_allow_file)-1] = '\0';

    strncpy(g_policy_file, argv[4], sizeof(g_policy_file)-1);
    g_policy_file[sizeof(g_policy_file)-1] = '\0';

    strncpy(g_root_dir, argv[5], sizeof(g_root_dir)-1);
    g_root_dir[sizeof(g_root_dir)-1] = '\0';

    /* Ensure FIFOs exist, then open them */
    create_fifo((char*)fifo_in);
    create_fifo((char*)fifo_out);

    g_in_fd = open_fifo_rd(fifo_in, 0);
    if (g_in_fd < 0) { LOG("Could not open input fifo %s\n", fifo_in); return 1; }

    g_out_fd = open_fifo_wr(fifo_out);
    if (g_out_fd < 0) { LOG("Could not open output fifo %s\n", fifo_out); return 1; }

    char line[IN_BUFFER_MAX_SIZE];

    int ep = make_epoll(&g_in_fd, 1);
    if (ep < 0) {
        LOG("Issue when creating epoll");
        return 1;
    }

    while (1) {
        struct epoll_event events[8];
        int n = epoll_wait(ep, events, 8, -1);
        if (n < 0) {
            if (errno == EINTR) continue;
            LOG("Error on epoll wait");
            break;
        }
        for(int i=0; i<n; ++i){
            if (events[i].events & EPOLLIN) {
                int err = read_line_fd(g_in_fd, line, IN_BUFFER_MAX_SIZE);
                if (line[0] == '\0') continue;
                if(err == 0){
                    if(strlen(line) == 0) continue;
                    handle_request(line);
                }
            }
        }
    }

    return 0;
}
