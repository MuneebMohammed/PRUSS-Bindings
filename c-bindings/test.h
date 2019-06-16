#include <stdio.h>
#include <string.h>
#include <sys/socket.h> 
#include <sys/un.h> 
#include <unistd.h> 
#include <errno.h>

bool sock_connect();
char* sendcmd(char* command);
bool sock_disconnect();

enum State{
    NONE,
    STOPPED,
    RUNNING,
    HALTED
};

struct Socket{
    int fd;
    const char* socketpath;
    struct sockaddr_un addr;
};

struct PRU{
    int number;
    int chanport;
    char *chanName;
    //Socket sock;
    State state = NONE;
};

struct PRUSS{
    bool on = false;
    //Socket sock;
    PRU pru0;
    PRU pru1;
};
