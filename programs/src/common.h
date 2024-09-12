
int setup(const char *const path, int *out_fd, char *out_fifo_path);
void cleanup(int fd, const char *const fifo_path);