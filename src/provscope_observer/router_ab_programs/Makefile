
CC = gcc
RM = rm -f
CFLAGS = -O0 -g -Wall -Wextra

SRC_DIR = src
BUILD_DIR = build
BUILD_OBJS_DIR = $(BUILD_DIR)/objs
BUILD_EXEC_DIR = $(BUILD_DIR)/exec
TMP_EXEC_FILES_DIR = $(BUILD_EXEC_DIR)/run
TMP_EXEC_FILES = allow goal

.PHONY: all clean setup


all: router.bin process_a.bin process_b.bin setup


clean:
	@$(RM) -r $(BUILD_DIR)


setup: 
	@$(RM) -r $(TMP_EXEC_FILES_DIR)
	@mkdir -p $(TMP_EXEC_FILES_DIR)
	@touch $(foreach file, $(TMP_EXEC_FILES), $(TMP_EXEC_FILES_DIR)/$(file))


router.bin: $(BUILD_OBJS_DIR)/router.o $(BUILD_OBJS_DIR)/common.o
process_a.bin: $(BUILD_OBJS_DIR)/process_a.o $(BUILD_OBJS_DIR)/common.o
process_b.bin: $(BUILD_OBJS_DIR)/process_b.o $(BUILD_OBJS_DIR)/common.o

%.bin:
	@if [ ! -d $(BUILD_EXEC_DIR) ]; then mkdir -p $(BUILD_EXEC_DIR); fi
	@$(CC) $^ $(CFLAGS) -o $(BUILD_EXEC_DIR)/$@


$(BUILD_OBJS_DIR)/%.o: $(SRC_DIR)/%.c
	@if [ ! -d $(dir $@) ]; then mkdir -p $(dir $@); fi
	@$(CC) $(CFLAGS) -I $(SRC_DIR) -c $< -o $@

