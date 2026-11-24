PROG = hello_world_example
OBJS = hello_world_example.o
INSTALL_DIR = install_artifact/usr/local/bin

.PHONY: all clean install

all: $(PROG)

$(PROG): $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

install: $(PROG)
	mkdir -p $(INSTALL_DIR)
	install -m 0755 $(PROG) $(INSTALL_DIR)/$(PROG)

clean:
	rm -f $(PROG) $(OBJS)
