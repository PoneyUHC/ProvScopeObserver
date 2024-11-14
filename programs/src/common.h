
int open_fifo(char *path, int *out_fd, int mode);
void close_fifo(int fd, char *fifo_path);

void get_time_str(char *destination);
void LOG(const char *format, ...);