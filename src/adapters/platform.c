#include "case_file.h"

#include <stdio.h>
#include <string.h>

static int readable(const char *utf8_path)
{
    FILE *file = rp_fopen_utf8_read(utf8_path);
    if (file == NULL) { return 0; }
    (void)fclose(file);
    return 1;
}

static int executable_folder(char *output, size_t capacity);

int rp_find_bundled_case(const char *relative, char *output, size_t capacity)
{
    char folder[1024];
    if (relative == NULL || output == NULL || capacity == 0U) { return 0; }
    if (readable(relative) && strlen(relative) < capacity) {
        (void)snprintf(output, capacity, "%s", relative);
        return 1;
    }
    if (!executable_folder(folder, sizeof(folder))) { return 0; }
    for (unsigned int up = 0U; up <= 4U; ++up) {
        char *slash;
        const int written = snprintf(output, capacity, "%s/%s", folder, relative);
        if (written > 0 && (size_t)written < capacity && readable(output)) { return 1; }
        slash = strrchr(folder, '/');
        if (slash == NULL) { break; }
        *slash = '\0';
    }
    return 0;
}

#ifdef _WIN32
#include <windows.h>
#include <stdlib.h>

/* UTF-8 folder of the running exe with '/' separators. */
static int executable_folder(char *output, size_t capacity)
{
    wchar_t wide[1024];
    const DWORD length = GetModuleFileNameW(NULL, wide, (DWORD)(sizeof(wide) / sizeof(wide[0])));
    char *slash;
    if (length == 0U || length >= sizeof(wide) / sizeof(wide[0])) { return 0; }
    if (WideCharToMultiByte(CP_UTF8, 0, wide, -1, output, (int)capacity, NULL, NULL) == 0) { return 0; }
    for (char *p = output; *p != '\0'; ++p) { if (*p == '\\') { *p = '/'; } }
    slash = strrchr(output, '/');
    if (slash == NULL) { return 0; }
    *slash = '\0';
    return 1;
}

FILE *rp_fopen_utf8_read(const char *utf8_path)
{
    const int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8_path, -1, NULL, 0);
    wchar_t *path;
    FILE *file;
    if (length <= 0) {
        return NULL;
    }
    path = malloc((size_t)length * sizeof(*path));
    if (path == NULL) {
        return NULL;
    }
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8_path, -1, path, length) == 0) {
        free(path);
        return NULL;
    }
    file = _wfopen(path, L"rb");
    free(path);
    return file;
}
#else
FILE *rp_fopen_utf8_read(const char *utf8_path)
{
    return fopen(utf8_path, "rb");
}

/* No portable exe-path query in C17; non-Windows builds resolve from the
 * current directory only. */
static int executable_folder(char *output, size_t capacity)
{
    (void)output; (void)capacity;
    return 0;
}
#endif
