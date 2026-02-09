
#include <stddef.h>

int create_fifo(char *path);
void close_fifo(int fd);

void get_time_str(char *destination);

#define ERR_NOTHING_TO_READ 1
#define ERR_READ_ERROR 2
int usual_read_errors(int n_read);

__attribute__((__format__(__printf__, 1, 2)))
void LOG(const char *format, ...);

// Convenience helpers for opening FIFOs
int open_fifo_rd(const char *path, int nonblock);
int open_fifo_wr(const char *path);

// Convenience helper for epoll
int make_epoll(const int *fifos, size_t n_fifos);