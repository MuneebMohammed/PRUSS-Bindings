#include "test.h"

int main(){
    PRUSS pruss;
    PRU p0 = pruss.pru0;
    PRUSS_init(&pruss);
    PRU_init(&p0, 0);
    PRU_enable(&p0);
    if(PRU_load(&p0, "./firmware_examples/rpmsg_echo/gen/rpmsg_echo.out"))
        printf("Firmware loaded\n");
    else
	return -1;
    char temp[] = "Hi there";
    PRU_sendMsg(&p0, temp);
    printf("Echoing: %s\n", temp);
    printf("Loopback: %s\n", PRU_getMsg(&p0));
    PRU_disable(&p0);
    PRUSS_shutDown(&pruss);
    return 0;
}
