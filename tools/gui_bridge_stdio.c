/* Development harness for the GUI bridge: one JSON request per stdin line,
 * one JSON envelope per stdout line. Used by tools/gui_dev.py (browser preview
 * without WebView2) and tests/test_gui.py. Not part of the shipped program. */
#include "gui_bridge.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LINE_MAX_BYTES 65536

int main(void)
{
    static char line[LINE_MAX_BYTES];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        size_t length = strlen(line);
        char *response;
        if (length > 0U && line[length - 1U] != '\n' && !feof(stdin)) {
            (void)fputs("{\"ok\":false,\"status\":\"parse_error\",\"message\":\"Request line too long.\"}\n", stdout);
            return 3;
        }
        while (length > 0U && (line[length - 1U] == '\n' || line[length - 1U] == '\r')) { line[--length] = '\0'; }
        if (length == 0U) { continue; }
        response = rp_gui_handle(line);
        if (response == NULL) {
            (void)fputs("{\"ok\":false,\"status\":\"io_error\",\"message\":\"Cannot allocate response.\"}\n", stdout);
        } else {
            (void)fputs(response, stdout);
            (void)fputc('\n', stdout);
            rp_gui_release(response);
        }
        if (fflush(stdout) != 0) { return 3; }
    }
    return 0;
}
