CC = gcc
CFLAGS = -Wall -g

SRC = src
BUILD = build/exec/

all: $(BUILD)/router $(BUILD)/user $(BUILD)/auth $(BUILD)/access

$(BUILD)/router: $(SRC)/router.c $(SRC)/common.c $(SRC)/common.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRC)/router.c $(SRC)/common.c

$(BUILD)/user: $(SRC)/user.c $(SRC)/common.c $(SRC)/common.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRC)/user.c $(SRC)/common.c

$(BUILD)/auth: $(SRC)/auth.c $(SRC)/common.c $(SRC)/common.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRC)/auth.c $(SRC)/common.c

$(BUILD)/access: $(SRC)/access.c $(SRC)/common.c $(SRC)/common.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRC)/access.c $(SRC)/common.c

clean:
	rm -rf build

.PHONY: all clean
