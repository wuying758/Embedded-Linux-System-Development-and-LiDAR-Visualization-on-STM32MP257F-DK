#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

static int read_line(char *buffer, size_t size)
{
    int c;

    if (fgets(buffer, size, stdin) == NULL)
        return 0;

    if (strchr(buffer, '\n') == NULL) {
        while ((c = getchar()) != '\n' && c != EOF)
            ;
    }

    buffer[strcspn(buffer, "\r\n")] = '\0';
    return 1;
}

static void show_greeting(void)
{
    puts("\nUser space example: hello world from STMicroelectronics");
}

int main(void)
{
    char choice[32];
    char text[256];
    struct utsname kernel;

    setvbuf(stdout, NULL, _IONBF, 0);
    show_greeting();

    for (;;) {
        puts("\n=== Hello World Serial Menu ===");
        puts("1) Show greeting");
        puts("2) Show kernel version");
        puts("3) Echo text");
        puts("4) Run countdown");
        puts("0) Exit to shell");
        printf("Select: ");

        if (!read_line(choice, sizeof(choice)) || strcmp(choice, "0") == 0)
            break;

        if (strcmp(choice, "1") == 0) {
            show_greeting();
        } else if (strcmp(choice, "2") == 0) {
            if (uname(&kernel) == 0)
                printf("Kernel: %s\n", kernel.release);
            else
                perror("uname");
        } else if (strcmp(choice, "3") == 0) {
            printf("Enter text: ");
            if (!read_line(text, sizeof(text)))
                break;
            printf("Echo: %s\n", text);
        } else if (strcmp(choice, "4") == 0) {
            for (int i = 10; i >= 0; --i) {
                printf("%d ", i);
                sleep(1);
            }
            putchar('\n');
        } else {
            puts("Invalid selection. Enter 0, 1, 2, 3, or 4.");
        }
    }

    puts("Returning to shell.");
    return 0;
}
