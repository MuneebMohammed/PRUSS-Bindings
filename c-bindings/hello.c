#include <stdio.h>

int main(){
    char temp[50];
    printf("Enter your name: \n");
    fgets(temp, 50, stdin);
    printf("You entered: %s\n", temp);
    return 0;
}
