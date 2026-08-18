
CC = gcc
RM = rm -f
CFLAGS = -O0 -g -Wall -Wextra -Wpedantic

SRC_DIR = src
BUILD_DIR = build
BUILD_OBJS_DIR = $(BUILD_DIR)/objs
BUILD_EXEC_DIR = $(BUILD_DIR)/exec
TMP_EXEC_FILES_DIR = $(BUILD_EXEC_DIR)/run
TMP_EXEC_FILES = logs goal

LAUNCHER = run.bin

CROSS_CC      = /home/loic/x-tools/powerpc64-e5500-linux-gnu/bin/powerpc64-e5500-linux-gnu-gcc
CROSS_CFLAGS  = $(CFLAGS) -m64 -mcpu=e5500
CROSS_DIR     = cross

.PHONY: all system launcher cross clean setup


all: system launcher


# the processes started by the launcher, which expects them to be already built
system: router.bin client.bin log_collector.bin setup


launcher: $(LAUNCHER)


# builds everything for the target under $(CROSS_DIR), keeping the layout the
# launcher expects : $(CROSS_DIR)/$(LAUNCHER) next to $(CROSS_DIR)/$(BUILD_EXEC_DIR).
# host and target objects never mix, as each has its own build directory
cross:
	@command -v $(CROSS_CC) > /dev/null || { echo "Cross compiler not found : $(CROSS_CC)"; exit 1; }
	@$(MAKE) all CC="$(CROSS_CC)" CFLAGS="$(CROSS_CFLAGS)" BUILD_DIR=$(CROSS_DIR)/$(BUILD_DIR) LAUNCHER=$(CROSS_DIR)/$(LAUNCHER)


clean:
	@$(RM) -r $(BUILD_DIR)
	@$(RM) -r $(CROSS_DIR)
	@$(RM) $(LAUNCHER)


setup:
	@$(RM) -r $(TMP_EXEC_FILES_DIR)
	@mkdir -p $(TMP_EXEC_FILES_DIR)
	@touch $(foreach file, $(TMP_EXEC_FILES), $(TMP_EXEC_FILES_DIR)/$(file))


router.bin: $(BUILD_OBJS_DIR)/router.o $(BUILD_OBJS_DIR)/common.o
client.bin: $(BUILD_OBJS_DIR)/client.o $(BUILD_OBJS_DIR)/common.o
log_collector.bin: $(BUILD_OBJS_DIR)/log_collector.o $(BUILD_OBJS_DIR)/common.o

%.bin:
	@if [ ! -d $(BUILD_EXEC_DIR) ]; then mkdir -p $(BUILD_EXEC_DIR); fi
	@$(CC) $^ $(CFLAGS) -o $(BUILD_EXEC_DIR)/$@


# the launcher lives next to the tracer it has to run, at the root of the system
$(LAUNCHER): $(BUILD_OBJS_DIR)/run.o $(BUILD_OBJS_DIR)/common.o
	@$(CC) $^ $(CFLAGS) -o $@


$(BUILD_OBJS_DIR)/%.o: $(SRC_DIR)/%.c
	@if [ ! -d $(dir $@) ]; then mkdir -p $(dir $@); fi
	@$(CC) $(CFLAGS) -I $(SRC_DIR) -c $< -o $@
