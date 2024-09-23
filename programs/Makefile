
CC = gcc
RM = rm -f
CXXFLAGS = -O0 -Wall -Wpedantic

SRC_DIR = src
BUILD_DIR = build
BUILD_OBJS_DIR = $(BUILD_DIR)/binaries
BUILD_EXEC_DIR = $(BUILD_DIR)/exec

SRCS = $(wildcard $(SRC_DIR)/*.c) $(wildcard $(SRC_DIR)/**/*.c)
OBJS =  $(patsubst %.c, %.o, $(SRCS))

OBJS_LOCATION = $(patsubst %.o, $(BUILD_OBJS_DIR)/%.o, $(OBJS))


.PHONY: all clean


all: router


clean:
	$(RM) $(OBJS_LOCATION)


router: $(BUILD_OBJS_DIR)/router.o $(BUILD_OBJS_DIR)/common.o
	@if [ ! -d $(BUILD_EXEC_DIR) ]; then mkdir -p $(BUILD_EXEC_DIR); fi
	@$(CC) $^ $(CFLAGS) -o $(BUILD_EXEC_DIR)/router


$(BUILD_OBJS_DIR)/%.o: $(SRC_DIR)/%.c Makefile
	@if [ ! -d $(dir $@) ]; then mkdir -p $(dir $@); fi
	@$(CC) $(CFLAGS) -I $(SRC_DIR) -c $< -o $@