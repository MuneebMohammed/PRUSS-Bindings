#include "test.h"

char err[4];
char rec[1024];

Socket sock;

/*int main(void){
     
    bool x = sock_connect();
    printf("%i\n",sock.fd);
    printf("%s\n",sock.socketpath);
    printf("%d\n", x);
    
    char commanda[] = "ENABLE_0";
    char *ret = sendcmd(commanda);
    printf("%s\n", ret);
    PRU p0 = pruss.pru0;
    PRU p1 = pruss.pru1;
    void change();
    return 0;
}*/

bool sock_connect(){
    sock.fd = -1;
    sock.socketpath = "/tmp/prussd.sock";   
    sock.fd = socket(AF_UNIX, SOCK_STREAM, 0);
    memset(&sock.addr, 0, sizeof(sock.addr));
    sock.addr.sun_family = AF_UNIX;
    strncpy(sock.addr.sun_path, sock.socketpath, sizeof(sock.addr.sun_path)-1);
    if(connect(sock.fd, (struct sockaddr*)&sock.addr, sizeof(sock.addr)) == -1)
        return false;

    return true;
}

char* sendcmd(char *command){
    if(!sock_connect()){ 
        sprintf(err, "%d", ECONNREFUSED);
        return err;
    }

    int nbytes;
    char buf[1024]; 
    nbytes = snprintf(buf, sizeof(buf), command); 
    buf[nbytes] = '\n';
    send(sock.fd, buf, strlen(buf), 0); 

    nbytes = recv(sock.fd, rec, sizeof(rec), 0); 
    rec[nbytes] = '\0'; 	

    sock_disconnect(); 
	
    return rec;

}

bool sock_disconnect(){
    if(sock.fd == -1)
        return false;
    close(sock.fd);
    sock.fd = -1;
    return true;
}


