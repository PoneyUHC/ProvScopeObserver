
int open_fifo(char *path, int *out_fd, int mode);
void close_fifo(int fd, const char *const fifo_path);