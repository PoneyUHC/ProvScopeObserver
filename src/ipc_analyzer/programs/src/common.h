
int create_fifo(char *path);
void close_fifo(int fd);

void get_time_str(char *destination);

__attribute__((__format__(__printf__, 1, 2)))
void LOG(const char *format, ...);