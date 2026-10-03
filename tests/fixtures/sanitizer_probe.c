/* Deliberate defects: executed only as negative controls in sanitizer builds. */
#include <limits.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) { return 2; }
    if (strcmp(argv[1], "undefined") == 0) {
        volatile int value = INT_MAX;
        volatile int increment = 1;
        return value + increment;
    }
    if (strcmp(argv[1], "address") == 0) {
        volatile size_t index = 16U;
        char *buffer = malloc(8U);
        if (buffer == NULL) { return 3; }
        buffer[index] = 'x';
        free(buffer);
        return 0;
    }
    return 2;
}
