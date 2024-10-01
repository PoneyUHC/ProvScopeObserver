
CC = gcc
RM = rm -f
CFLAGS = -O0 -Wall -Wpedantic

SRC_DIR = src
BUILD_DIR = build
BUILD_OBJS_DIR = $(BUILD_DIR)/binaries
BUILD_EXEC_DIR = $(BUILD_DIR)/exec
TMP_EXEC_FILES_DIR = $(BUILD_EXEC_DIR)/run
TMP_EXEC_FILES = logs

.PHONY: all clean


all: router.exe target.exe log_collector.exe attacker.exe setup


clean:
	$(RM) -r $(BUILD_DIR)


setup:
	@mkdir -p $(TMP_EXEC_FILES_DIR)
	@touch $(foreach file, $(TMP_EXEC_FILES), $(TMP_EXEC_FILES_DIR)/$(file))


router.exe: $(BUILD_OBJS_DIR)/router.o $(BUILD_OBJS_DIR)/common.o
target.exe: $(BUILD_OBJS_DIR)/target.o $(BUILD_OBJS_DIR)/common.o
log_collector.exe: $(BUILD_OBJS_DIR)/log_collector.o $(BUILD_OBJS_DIR)/common.o
attacker.exe: $(BUILD_OBJS_DIR)/attacker.o $(BUILD_OBJS_DIR)/common.o

%.exe:
	@if [ ! -d $(BUILD_EXEC_DIR) ]; then mkdir -p $(BUILD_EXEC_DIR); fi
	@$(CC) $^ $(CFLAGS) -o $(BUILD_EXEC_DIR)/$@


$(BUILD_OBJS_DIR)/%.o: $(SRC_DIR)/%.c
	@if [ ! -d $(dir $@) ]; then mkdir -p $(dir $@); fi
	@$(CC) $(CFLAGS) -I $(SRC_DIR) -c $< -o $@