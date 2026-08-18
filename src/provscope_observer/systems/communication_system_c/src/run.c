
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <errno.h>
#include <libgen.h>
#include <sys/types.h>
#include <sys/wait.h>

#include "common.h"


#define ERR_BAD_ARG 1
#define ERR_RUNTIME 2

#define MIN_TALK_DELAY_MICROSECONDS 50000

#define POLL_DELAY_MICROSECONDS 200000
#define TERMINATION_TIMEOUT_MICROSECONDS 2000000
#define TERMINATION_POLL_MICROSECONDS 50000
#define FIFO_WAIT_TIMEOUT_MICROSECONDS 2000000
#define FIFO_WAIT_POLL_MICROSECONDS 10000

#define PATH_MAX_LEN 256
#define EXE_PATH_MAX_LEN 4096
#define NUMBER_MAX_LEN 16

// the tracer sits next to this launcher and starts the system processes for us:
// ./tracer -o [process_name].logs [process_to_execute] [process arguments]*
#define TRACER_NAME "tracer"
#define TRACER_LOG_OPTION "-o"

#define EXEC_DIR "build/exec"

#define ROUTER_BIN "./router.bin"
#define CLIENT_BIN "./client.bin"
#define LOG_COLLECTOR_BIN "./log_collector.bin"

#define ROUTER_LOG_FILE "run/router.logs"
#define CLIENT_LOG_FILE_FORMAT "run/client%d.logs"
#define LOG_COLLECTOR_LOG_FILE "run/log_c.logs"

#define ROUTER_TO_CLIENT_FIFO_FORMAT "run/r_client%d"
#define CLIENT_TO_ROUTER_FIFO_FORMAT "run/client%d_r"
#define ANY_TO_LOG_COLLECTOR_FIFO "run/any_l"

#define LOG_FILE "run/logs"
#define GOAL_FILE "run/goal"


static volatile sig_atomic_t g_kill_now = 0;

static char g_tracer_path[PATH_MAX_LEN];

static pid_t *g_procs = NULL;
static int g_n_procs = 0;


void exit_gracefully(int signum)
{
    (void) signum;
    g_kill_now = 1;
}


void watch_end_process()
{
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = exit_gracefully;

    sigaction(SIGINT, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
}


int get_script_dir(char *destination, size_t size)
{
    char exe_path[EXE_PATH_MAX_LEN];

    ssize_t n_read = readlink("/proc/self/exe", exe_path, EXE_PATH_MAX_LEN - 1);
    if(n_read == -1){
        LOG("Could not resolve the path of this executable\n");
        return ERR_RUNTIME;
    }
    exe_path[n_read] = '\0';

    char *dir = dirname(exe_path);
    if(strlen(dir) >= size){
        LOG("Directory path too long : %s\n", dir);
        return ERR_RUNTIME;
    }

    strcpy(destination, dir);

    return 0;
}


int find_tracer(const char *script_dir)
{
    int written = snprintf(g_tracer_path, PATH_MAX_LEN, "%s/%s", script_dir, TRACER_NAME);
    if(written >= PATH_MAX_LEN){
        LOG("Path of the tracer too long : %s/%s\n", script_dir, TRACER_NAME);
        return ERR_RUNTIME;
    }

    if(access(g_tracer_path, X_OK) != 0){
        LOG("Could not find an executable tracer at %s\n", g_tracer_path);
        return ERR_RUNTIME;
    }

    return 0;
}


// the system processes are expected to be already built
int check_system_binaries()
{
    char *binaries[] = {ROUTER_BIN, CLIENT_BIN, LOG_COLLECTOR_BIN};

    for(size_t i=0; i<sizeof(binaries)/sizeof(binaries[0]); ++i){
        if(access(binaries[i], X_OK) != 0){
            LOG("Could not find an executable %s in %s\n", binaries[i], EXEC_DIR);
            return ERR_RUNTIME;
        }
    }

    return 0;
}


// runs [argv] under the tracer, which writes the process logs to [log_path]
pid_t spawn_traced(char *log_path, char **argv)
{
    int n_args = 0;
    while(argv[n_args] != NULL){
        ++n_args;
    }

    // tracer + log option + log file + process and its arguments + NULL
    char **tracer_argv = (char**) malloc((n_args + 4) * sizeof(char*));
    if(tracer_argv == NULL){
        LOG("Could not allocate the tracer command line for %s\n", argv[0]);
        return -1;
    }

    tracer_argv[0] = g_tracer_path;
    tracer_argv[1] = TRACER_LOG_OPTION;
    tracer_argv[2] = log_path;
    for(int i=0; i<n_args; ++i){
        tracer_argv[3+i] = argv[i];
    }
    tracer_argv[3+n_args] = NULL;

    pid_t pid = fork();
    if(pid == -1){
        LOG("Could not fork to start %s\n", argv[0]);
        free(tracer_argv);
        return -1;
    }

    if(pid == 0){
        execv(g_tracer_path, tracer_argv);
        LOG("Could not run the tracer on %s\n", argv[0]);
        _exit(127);
    }

    LOG("Started %s under the tracer (pid %d), logs in %s\n", argv[0], pid, log_path);

    free(tracer_argv);

    return pid;
}


void free_paths(char **paths, int n_paths)
{
    if(paths == NULL){
        return;
    }

    for(int i=0; i<n_paths; ++i){
        free(paths[i]);
    }
    free(paths);
}


char **make_paths(const char *format, int n_paths)
{
    char **paths = (char**) malloc(n_paths * sizeof(char*));
    if(paths == NULL){
        return NULL;
    }

    for(int i=0; i<n_paths; ++i){
        paths[i] = (char*) malloc(PATH_MAX_LEN);
        if(paths[i] == NULL){
            free_paths(paths, i);
            return NULL;
        }
        snprintf(paths[i], PATH_MAX_LEN, format, i);
    }

    return paths;
}


int start_router(int n_clients, char *n_clients_str, char **clients_to_router, char **router_to_clients)
{
    // ./router.bin [n_targets] [log_filename] [fifo_in]* [fifo_out]*
    char **argv = (char**) malloc((4 + 2*n_clients) * sizeof(char*));
    if(argv == NULL){
        LOG("Could not allocate the router command line\n");
        return ERR_RUNTIME;
    }

    argv[0] = ROUTER_BIN;
    argv[1] = n_clients_str;
    argv[2] = LOG_FILE;
    for(int i=0; i<n_clients; ++i){
        argv[3+i] = clients_to_router[i];
        argv[3+n_clients+i] = router_to_clients[i];
    }
    argv[3+2*n_clients] = NULL;

    pid_t pid = spawn_traced(ROUTER_LOG_FILE, argv);

    free(argv);

    if(pid == -1){
        return ERR_RUNTIME;
    }

    g_procs[g_n_procs++] = pid;

    return 0;
}


// every fifo of the system is created by the router : clients can only be
// started once those are in place
int wait_for_fifos(char **paths, int n_paths)
{
    for(int waited=0; waited<FIFO_WAIT_TIMEOUT_MICROSECONDS; waited+=FIFO_WAIT_POLL_MICROSECONDS){

        int n_missing = 0;
        for(int i=0; i<n_paths; ++i){
            if(access(paths[i], F_OK) != 0){
                ++n_missing;
            }
        }

        if(n_missing == 0){
            return 0;
        }

        usleep(FIFO_WAIT_POLL_MICROSECONDS);
    }

    LOG("Timed out while waiting for the router to create its fifos\n");

    return ERR_RUNTIME;
}


int start_clients(int n_clients, char *n_clients_str, char *talk_delay_str, char **clients_to_router, char **router_to_clients)
{
    for(int i=0; i<n_clients; ++i){

        char log_path[PATH_MAX_LEN];
        snprintf(log_path, PATH_MAX_LEN, CLIENT_LOG_FILE_FORMAT, i);

        char my_id[NUMBER_MAX_LEN];
        snprintf(my_id, NUMBER_MAX_LEN, "%d", i);

        char *petitfilou = (i == 0) ? "1" : "0";

        // ./client.bin [petitfilou] [fifo_in] [fifo_out] [n_clients] [my_id] [talk_delay_ms]
        char *argv[] = {
            CLIENT_BIN,
            petitfilou,
            router_to_clients[i],
            clients_to_router[i],
            n_clients_str,
            my_id,
            talk_delay_str,
            NULL
        };

        pid_t pid = spawn_traced(log_path, argv);
        if(pid == -1){
            return ERR_RUNTIME;
        }

        g_procs[g_n_procs++] = pid;
    }

    return 0;
}


int start_log_collector()
{
    // ./log_collector.bin [log_file] [fifo_in] [goal_file]
    char *argv[] = {LOG_COLLECTOR_BIN, LOG_FILE, ANY_TO_LOG_COLLECTOR_FIFO, GOAL_FILE, NULL};

    pid_t pid = spawn_traced(LOG_COLLECTOR_LOG_FILE, argv);
    if(pid == -1){
        return ERR_RUNTIME;
    }

    g_procs[g_n_procs++] = pid;

    return 0;
}


int start(int n_clients, int talk_delay_microsecond)
{
    // router, clients and log collector
    g_procs = (pid_t*) malloc((n_clients + 2) * sizeof(pid_t));
    if(g_procs == NULL){
        LOG("Could not allocate the process list\n");
        return ERR_RUNTIME;
    }

    char **router_to_clients = make_paths(ROUTER_TO_CLIENT_FIFO_FORMAT, n_clients);
    char **clients_to_router = make_paths(CLIENT_TO_ROUTER_FIFO_FORMAT, n_clients);
    if(router_to_clients == NULL || clients_to_router == NULL){
        LOG("Could not allocate the fifo paths\n");
        free_paths(router_to_clients, n_clients);
        free_paths(clients_to_router, n_clients);
        return ERR_RUNTIME;
    }

    char n_clients_str[NUMBER_MAX_LEN];
    snprintf(n_clients_str, NUMBER_MAX_LEN, "%d", n_clients);

    char talk_delay_str[NUMBER_MAX_LEN];
    snprintf(talk_delay_str, NUMBER_MAX_LEN, "%d", talk_delay_microsecond);

    int err = start_router(n_clients, n_clients_str, clients_to_router, router_to_clients);
    if(!err){
        err = wait_for_fifos(clients_to_router, n_clients);
    }
    if(!err){
        err = wait_for_fifos(router_to_clients, n_clients);
    }
    if(!err){
        err = start_clients(n_clients, n_clients_str, talk_delay_str, clients_to_router, router_to_clients);
    }
    if(!err){
        err = start_log_collector();
    }

    free_paths(router_to_clients, n_clients);
    free_paths(clients_to_router, n_clients);

    return err;
}


void wait_for_processes()
{
    for(int waited=0; waited<TERMINATION_TIMEOUT_MICROSECONDS; waited+=TERMINATION_POLL_MICROSECONDS){

        int n_running = 0;
        for(int i=0; i<g_n_procs; ++i){
            if(g_procs[i] == -1){
                continue;
            }

            pid_t done = waitpid(g_procs[i], NULL, WNOHANG);
            if(done == g_procs[i] || (done == -1 && errno == ECHILD)){
                g_procs[i] = -1;
            } else {
                ++n_running;
            }
        }

        if(n_running == 0){
            return;
        }

        usleep(TERMINATION_POLL_MICROSECONDS);
    }

    for(int i=0; i<g_n_procs; ++i){
        if(g_procs[i] == -1){
            continue;
        }
        LOG("Process %d did not terminate, killing it\n", g_procs[i]);
        kill(g_procs[i], SIGKILL);
        waitpid(g_procs[i], NULL, 0);
    }
}


void clean()
{
    for(int i=0; i<g_n_procs; ++i){
        kill(g_procs[i], SIGTERM);
    }

    wait_for_processes();

    free(g_procs);
    g_procs = NULL;
    g_n_procs = 0;
}


int main(int argc, char *argv[])
{
    setvbuf(stdout, NULL, _IONBF, 0);

    if(argc != 3){
        LOG("Usage: %s [n_targets] [talk_delay_ms]\n", argv[0]);
        return ERR_BAD_ARG;
    }

    int n_clients = atoi(argv[1]);
    if(n_clients < 1){
        LOG("Number of targets must be in at least 1\n");
        return ERR_BAD_ARG;
    }

    int talk_delay_microsecond = atoi(argv[2]);
    if(talk_delay_microsecond < MIN_TALK_DELAY_MICROSECONDS){
        LOG("talk_delay_ms must be at least %d (or else the trace may be too heavy for the tool)\n", MIN_TALK_DELAY_MICROSECONDS);
        return ERR_BAD_ARG;
    }

    watch_end_process();

    char script_dir[PATH_MAX_LEN];
    if(get_script_dir(script_dir, PATH_MAX_LEN)){
        return ERR_RUNTIME;
    }

    if(find_tracer(script_dir)){
        return ERR_RUNTIME;
    }

    if(chdir(script_dir) == -1){
        LOG("Could not enter directory %s\n", script_dir);
        return ERR_RUNTIME;
    }

    if(chdir(EXEC_DIR) == -1){
        LOG("Could not enter directory %s\n", EXEC_DIR);
        return ERR_RUNTIME;
    }

    if(check_system_binaries()){
        return ERR_RUNTIME;
    }

    if(start(n_clients, talk_delay_microsecond)){
        clean();
        return ERR_RUNTIME;
    }

    while(!g_kill_now){
        usleep(POLL_DELAY_MICROSECONDS);
    }

    clean();

    return 0;
}
