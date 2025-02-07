
int open_fifo(char *path, int *out_fd, int mode);
void close_fifo(int fd);

void get_time_str(char *destination);

__attribute__((__format__(__printf__, 1, 2)))
void LOG(const char *format, ...);