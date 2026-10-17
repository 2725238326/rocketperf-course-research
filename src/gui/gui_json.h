#ifndef ROCKETPERF_GUI_JSON_H
#define ROCKETPERF_GUI_JSON_H

#include <stddef.h>

/* Flat GUI request: {"cmd":"name","args":{"key":number|"text"|true|false|[numbers]}}.
 * webview wraps call arguments in a JSON array, so a single-element [ {...} ]
 * is accepted too. Nested objects, non-finite numbers, duplicate keys and
 * unknown escapes are rejected; this is an IPC format, not a general parser. */
#define RP_GUI_KEY_MAX 48U
#define RP_GUI_TEXT_MAX 128U
#define RP_GUI_ARRAY_MAX 96U
#define RP_GUI_FIELD_MAX 40U

typedef enum { RP_GUI_NUMBER = 1, RP_GUI_TEXT, RP_GUI_BOOL, RP_GUI_ARRAY } RpGuiKind;

typedef struct {
    char key[RP_GUI_KEY_MAX];
    RpGuiKind kind;
    double number;
    int boolean;
    char text[RP_GUI_TEXT_MAX];
    double array[RP_GUI_ARRAY_MAX];
    size_t count;
} RpGuiField;

typedef struct {
    char cmd[RP_GUI_KEY_MAX];
    RpGuiField fields[RP_GUI_FIELD_MAX];
    size_t count;
} RpGuiRequest;

/* Returns 1 on success; on failure writes a short reason and returns 0. */
int rp_gui_parse(const char *text, RpGuiRequest *output, char *reason, size_t capacity);
const RpGuiField *rp_gui_field(const RpGuiRequest *request, const char *key);

/* Growable UTF-8 output. Any allocation failure latches `failed`; callers check
 * once at the end. Objects/arrays close by replacing a trailing comma. */
typedef struct {
    char *data;
    size_t length;
    size_t capacity;
    int failed;
} RpGuiBuffer;

void rp_gui_buffer_free(RpGuiBuffer *buffer);
void rp_gui_raw(RpGuiBuffer *buffer, const char *text);
void rp_gui_open(RpGuiBuffer *buffer, char bracket);
void rp_gui_close(RpGuiBuffer *buffer, char bracket);
void rp_gui_key(RpGuiBuffer *buffer, const char *key);
void rp_gui_string(RpGuiBuffer *buffer, const char *text);
void rp_gui_number(RpGuiBuffer *buffer, double value);
void rp_gui_num(RpGuiBuffer *buffer, const char *key, double value);
void rp_gui_text(RpGuiBuffer *buffer, const char *key, const char *text);
void rp_gui_flag(RpGuiBuffer *buffer, const char *key, int value);
void rp_gui_numbers(RpGuiBuffer *buffer, const char *key, const double *values, size_t count);

#endif
