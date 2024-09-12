
#include "common.h"

void work();

int main(int argc, char *argv[])
{
    int fd;
    char fifo[128];

    int err = setup(argv[1], &fd, fifo);
    if(err){
        return 1;
    }
    
    work();

    cleanup(fd, fifo);
}


void work()
{
    
}

