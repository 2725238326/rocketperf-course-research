#include "case_file.h"

#ifdef _WIN32
#include <windows.h>
#include <stdlib.h>

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
#endif
