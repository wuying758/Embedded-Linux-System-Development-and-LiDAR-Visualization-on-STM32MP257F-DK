#include <stdio.h>
#include <unistd.h>

int main(void)
{
    int i = 11;

    printf("\nUser space example: hello world from STMicroelectronics\n");
    setbuf(stdout, NULL);

    while (i--) {
        printf("%i ", i);
        sleep(1);
    }

    printf("\nUser space example: goodbye from STMicroelectronics\n");
    return 0;
}
