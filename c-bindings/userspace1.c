#include "test.h"

int main(){
    PRUSS pruss;
    PRUSS_init(&pruss);
    PRU p1 = pruss.pru1;
    PRU_init(&p1, 1);
    PRU_enable(&p1);
    /*if(PRU_load(&p0, "/home/debian/work/my/PRUSS-Bindings/c/firmware_examples/rpmsg_echo/gen/rpmsg_echo.out")){
        printf("Firmware loaded\n");
    }
    else
	return -1;
        */
    char temp[50];

    printf("Enter a word to be sent via the RPMsg channel: ");
    scanf("%s\n", temp);
    PRU_sendMsg(&p1, temp);
    //printf("%i\n", p1.chanPort);
    //exit(0);
    PRU_showRegs(&p1);
    printf("Loopback: %s\n", PRU_getMsg(&p1));
    PRU_disable(&p1);
    PRUSS_shutDown(&pruss);
    return 0;
}
